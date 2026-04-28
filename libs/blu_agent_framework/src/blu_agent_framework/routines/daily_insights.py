"""
Phase 2 (I2.1, I2.3, I2.4) — daily insights routine.

Pipeline (per tenant):

    1. Pull KPI snapshots for finance/commercial/inventory/supply (+ marketing for PRO)
       from analytics_v2 dimension RPCs, both for the current period and the
       trailing 30-day baseline.
    2. Render the `fragment/anomaly-detection` prompt (Langfuse → in-repo fallback)
       and ask the LLM to emit a JSON list of top-N insights.
    3. Upsert each insight via `public.record_insight(...)` (service-role).
    4. If the tenant has an enabled `client_routines` row for routine_id
       `daily_insights` with `notify_channel='whatsapp'` AND tier ∈ PRO set,
       send a WhatsApp digest via `blu_twilio_client`.
    5. Append a single `audit_log` entry summarising the run.

Trigger paths
─────────────
- CLI: `python -m blu_agent_framework.routines.daily_insights --client-id <uuid>`
- Cloud Scheduler / pg_cron + pg_net hitting a small HTTP wrapper (TBD).

Design notes
────────────
- We do NOT spin up the full LangGraph supervisor for this routine — the work
  is deterministic data-fetching + a single LLM call. Going through
  `blu_agent_framework.AgentBuilder` would require an MCP server, Redis
  checkpointer, and tool round-trips which add latency and surface area for
  no benefit.
- The worker is service-role only (it must read every tenant's KPIs and write
  to `client_insights`). No JWT plumbing.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier gating for WhatsApp digest (I2.3)
# ---------------------------------------------------------------------------

PRO_TIERS: frozenset[str] = frozenset({"SME", "PREMIUM", "ENTERPRISE"})

# KPIs we monitor per dimension, with metadata for the prompt input. Keep this
# in sync with §6 of the MVP roadmap and the analytics_v2 dimension RPCs
# (supabase/migrations/20260426234500_phase1_dimension_indicators.sql).
KPI_CATALOG: dict[str, list[dict[str, Any]]] = {
    "finance": [
        {"kpi": "receita_liquida",          "label": "Receita líquida",            "unit": "BRL", "direction": "higher_is_better"},
        {"kpi": "custo_total",              "label": "Custo total",                "unit": "BRL", "direction": "lower_is_better"},
        {"kpi": "margem_bruta_perc",        "label": "Margem bruta (%)",           "unit": "%",   "direction": "higher_is_better"},
        {"kpi": "ticket_medio",             "label": "Ticket médio",               "unit": "BRL", "direction": "higher_is_better"},
        {"kpi": "crescimento_receita_perc", "label": "Crescimento de receita (%)", "unit": "%",   "direction": "higher_is_better"},
    ],
    "commercial": [
        {"kpi": "total_pedidos",           "label": "Pedidos no período",        "unit": "count", "direction": "higher_is_better"},
        {"kpi": "ticket_medio",            "label": "Ticket médio",              "unit": "BRL",   "direction": "higher_is_better"},
        {"kpi": "novos_clientes",          "label": "Novos clientes",            "unit": "count", "direction": "higher_is_better"},
        {"kpi": "clientes_ativos",         "label": "Clientes ativos",           "unit": "count", "direction": "higher_is_better"},
        {"kpi": "taxa_recorrencia_perc",   "label": "Taxa de recorrência (%)",   "unit": "%",     "direction": "higher_is_better"},
    ],
    "inventory": [
        {"kpi": "skus_ativos",        "label": "SKUs ativos",         "unit": "count", "direction": "higher_is_better"},
        {"kpi": "skus_sem_estoque",   "label": "SKUs sem estoque",    "unit": "count", "direction": "lower_is_better"},
        {"kpi": "stockout_rate_perc", "label": "Stockout rate (%)",   "unit": "%",     "direction": "lower_is_better"},
        {"kpi": "giro_estoque",       "label": "Giro de estoque",     "unit": "count", "direction": "higher_is_better"},
        {"kpi": "dias_cobertura",     "label": "Dias de cobertura",   "unit": "days",  "direction": "higher_is_better"},
    ],
    "supply": [
        {"kpi": "rfqs_abertas",            "label": "RFQs abertas",                   "unit": "count", "direction": "higher_is_better"},
        {"kpi": "taxa_resposta_rfq_perc",  "label": "Taxa de resposta de RFQ (%)",    "unit": "%",     "direction": "higher_is_better"},
        {"kpi": "tempo_medio_resposta_h",  "label": "Tempo médio de resposta (h)",    "unit": "days",  "direction": "lower_is_better"},
        {"kpi": "pos_aprovadas",           "label": "POs aprovadas",                  "unit": "count", "direction": "higher_is_better"},
    ],
    "marketing": [  # PRO-only
        {"kpi": "novos_clientes",  "label": "Novos clientes (marketing)", "unit": "count", "direction": "higher_is_better"},
    ],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class KpiSnapshot:
    """A single KPI ready to feed the anomaly-detection prompt."""

    dimension: str
    kpi: str
    label: str
    value: float | None
    baseline: float | None
    stddev: float | None
    unit: str
    direction: str

    def to_prompt_dict(self, window_days: int) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "kpi": self.kpi,
            "label": self.label,
            "value": self.value,
            "baseline": self.baseline,
            "baseline_window_days": window_days,
            "stddev": self.stddev,
            "unit": self.unit,
            "direction": self.direction,
        }


@dataclass
class RoutineRunResult:
    client_id: str
    insights_written: int = 0
    insights_returned: int = 0
    notification_sent: bool = False
    skipped: str | None = None
    error: str | None = None
    duration_ms: int = 0
    payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def run_for_client(
    client_id: str,
    *,
    period: str = "30d",
    window_days: int = 30,
    max_insights: int = 5,
    db: Any | None = None,
    twilio: Any | None = None,
    today: date | None = None,
) -> RoutineRunResult:
    """Run the daily insights pipeline for a single tenant."""

    start = datetime.now(timezone.utc)
    today = today or start.date()
    result = RoutineRunResult(client_id=client_id, payload={"period": period, "window_days": window_days})

    try:
        from blu_supabase_client import get_supabase_client

        db = db or get_supabase_client(use_service_role=True)

        tenant = _fetch_tenant(db, client_id)
        if tenant is None:
            result.skipped = "tenant_not_found"
            return _finalise(result, start, db, today)

        snapshots = _build_snapshots(
            db,
            client_id=client_id,
            period=period,
            window_days=window_days,
            include_marketing=tenant.get("tier", "BASIC") in PRO_TIERS,
        )
        result.payload["snapshot_count"] = len(snapshots)

        insights = await _ask_llm(
            snapshots=snapshots,
            client_id=client_id,
            window_days=window_days,
            max_insights=max_insights,
        )
        result.insights_returned = len(insights)

        for insight in insights:
            _record_insight(db, client_id=client_id, run_date=today, insight=insight)
            result.insights_written += 1

        # I2.3 — WhatsApp digest (PRO + opt-in)
        result.notification_sent = _maybe_send_whatsapp_digest(
            db,
            tenant=tenant,
            insights=insights,
            twilio=twilio,
        )

        return _finalise(result, start, db, today)
    except Exception as exc:  # noqa: BLE001 — caller-facing routine: log+audit, never raise
        logger.exception("daily_insights run failed for %s", client_id)
        result.error = f"{type(exc).__name__}: {exc}"
        return _finalise(result, start, db, today)


async def run_all_enabled(
    *,
    period: str = "30d",
    window_days: int = 30,
    max_insights: int = 5,
    db: Any | None = None,
    concurrency: int = 4,
) -> list[RoutineRunResult]:
    """Iterate every active tenant and run :func:`run_for_client` per row."""

    from blu_supabase_client import get_supabase_client

    db = db or get_supabase_client(use_service_role=True)
    tenants = (
        db.table("clientes_blu")
        .select("client_id")
        .execute()
        .data
        or []
    )
    sem = asyncio.Semaphore(max(concurrency, 1))

    async def _bound(client_id: str) -> RoutineRunResult:
        async with sem:
            return await run_for_client(
                client_id,
                period=period,
                window_days=window_days,
                max_insights=max_insights,
                db=db,
            )

    return await asyncio.gather(*(_bound(t["client_id"]) for t in tenants))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_tenant(db: Any, client_id: str) -> dict[str, Any] | None:
    rows = (
        db.table("clientes_blu")
        .select("client_id, nome_empresa, tier")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    tenant = dict(rows[0])
    tenant["tier"] = (tenant.get("tier") or "BASIC").upper()
    return tenant


def _build_snapshots(
    db: Any,
    *,
    client_id: str,
    period: str,
    window_days: int,
    include_marketing: bool,
) -> list[KpiSnapshot]:
    """Pull current + trailing-Nd values for each KPI we monitor."""

    snapshots: list[KpiSnapshot] = []
    dimensions = ["finance", "commercial", "inventory", "supply"]
    if include_marketing:
        dimensions.append("marketing")

    for dimension in dimensions:
        current = _call_indicator_rpc(db, dimension, client_id=client_id, period=period)
        baseline = _call_indicator_rpc(db, dimension, client_id=client_id, period=f"{window_days}d")
        for spec in KPI_CATALOG[dimension]:
            value = _coerce_number(current.get(spec["kpi"]))
            base = _coerce_number(baseline.get(spec["kpi"]))
            stddev = None
            # If current period itself is the trailing window, baseline == value;
            # we can't synthesise a stddev from one observation, so leave it null
            # and let the prompt fall back to the threshold rule.
            snapshots.append(
                KpiSnapshot(
                    dimension=dimension,
                    kpi=spec["kpi"],
                    label=spec["label"],
                    value=value,
                    baseline=base,
                    stddev=stddev,
                    unit=spec["unit"],
                    direction=spec["direction"],
                )
            )
    return snapshots


def _call_indicator_rpc(db: Any, dimension: str, *, client_id: str, period: str) -> dict[str, Any]:
    """Call analytics_v2.get_indicators_for_client (service-role wrapper)."""

    try:
        resp = (
            db.schema("analytics_v2")
            .rpc(
                "get_indicators_for_client",
                {
                    "p_client_id": client_id,
                    "p_dimension": dimension,
                    "p_period":    period,
                },
            )
            .execute()
        )
        data = resp.data or {}
        if isinstance(data, list):
            return data[0] if data else {}
        if isinstance(data, dict):
            return data
        return {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_indicators_for_client(%s) failed for %s: %s", dimension, client_id, exc)
        return {}


def _coerce_number(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


async def _ask_llm(
    *,
    snapshots: list[KpiSnapshot],
    client_id: str,
    window_days: int,
    max_insights: int,
) -> list[dict[str, Any]]:
    """Render the anomaly-detection prompt and parse the JSON response."""

    if not snapshots:
        return []

    from blu_llm_service import ModelTier, get_model
    from blu_prompt_management import PromptLoader

    loader = PromptLoader()
    prompt = await loader.load(
        "fragment/anomaly-detection",
        variables={
            "kpi_snapshots": json.dumps(
                [s.to_prompt_dict(window_days) for s in snapshots],
                ensure_ascii=False,
                default=str,
            ),
            "client_id": client_id,
            "window_days": window_days,
            "max_insights": max_insights,
            "language": "pt-BR",
        },
        allow_fallback=True,
    )

    model = get_model(
        tier=ModelTier.DEFAULT,
        tags=["routine.daily_insights"],
    )

    response = await asyncio.to_thread(
        model.invoke,
        [
            prompt.as_system_message(),
            {
                "role": "user",
                "content": "Gere os insights conforme as regras. Responda apenas com JSON.",
            },
        ],
    )
    raw = getattr(response, "content", None) or str(response)
    insights = _parse_insights_json(raw)

    by_kpi = {(s.dimension, s.kpi): s for s in snapshots}
    cleaned: list[dict[str, Any]] = []
    for entry in insights[: max_insights]:
        dim = (entry.get("dimension") or "").strip()
        kpi = (entry.get("kpi") or "").strip()
        snap = by_kpi.get((dim, kpi))
        if snap is None:
            logger.debug("dropping insight for unknown kpi %s/%s", dim, kpi)
            continue
        cleaned.append(
            {
                "dimension": dim,
                "kpi": kpi,
                "severity": entry.get("severity", "info") if entry.get("severity") in ("info", "warning", "error") else "info",
                "title": (entry.get("title") or snap.label)[:200],
                "observation": (entry.get("observation") or "").strip(),
                "recommendation": (entry.get("recommendation") or "").strip() or None,
                "metric_value": _coerce_number(entry.get("metric_value", snap.value)),
                "baseline_value": _coerce_number(entry.get("baseline_value", snap.baseline)),
                "variance_pct": _coerce_number(entry.get("variance_pct")),
                "prompt_version": prompt.version,
            }
        )
    return cleaned


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_insights_json(raw: str) -> list[dict[str, Any]]:
    raw = (raw or "").strip()
    if not raw:
        return []
    # Strip ```json fences if a non-strict model emitted them.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(raw)
        if not match:
            logger.warning("anomaly-detection: could not parse JSON: %s", raw[:200])
            return []
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            logger.warning("anomaly-detection: JSON salvage failed: %s", exc)
            return []

    if isinstance(payload, dict):
        items = payload.get("insights")
    else:
        items = payload
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict)]


# ---------------------------------------------------------------------------
# Persistence + audit + notification
# ---------------------------------------------------------------------------


def _record_insight(db: Any, *, client_id: str, run_date: date, insight: dict[str, Any]) -> None:
    db.rpc(
        "record_insight",
        {
            "p_client_id":      client_id,
            "p_dimension":      insight["dimension"],
            "p_kpi":            insight["kpi"],
            "p_title":          insight["title"],
            "p_observation":    insight["observation"],
            "p_severity":       insight["severity"],
            "p_recommendation": insight["recommendation"],
            "p_metric_value":   insight["metric_value"],
            "p_baseline_value": insight["baseline_value"],
            "p_variance_pct":   insight["variance_pct"],
            "p_payload":        {},
            "p_run_date":       run_date.isoformat(),
            "p_prompt_version": insight.get("prompt_version"),
        },
    ).execute()


def _maybe_send_whatsapp_digest(
    db: Any,
    *,
    tenant: dict[str, Any],
    insights: list[dict[str, Any]],
    twilio: Any | None,
) -> bool:
    if not insights:
        return False
    if (tenant.get("tier") or "BASIC").upper() not in PRO_TIERS:
        return False

    client_id = tenant["client_id"]
    rows = (
        db.table("client_routines")
        .select("enabled, notify_channel, config")
        .eq("client_id", client_id)
        .eq("routine_id", "daily_insights")
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return False
    routine = rows[0]
    if not routine.get("enabled") or routine.get("notify_channel") != "whatsapp":
        return False
    phone = (routine.get("config") or {}).get("phone_e164")
    if not phone:
        logger.info("daily_insights: client %s opted in for whatsapp but has no phone_e164", client_id)
        return False

    try:
        if twilio is None:
            from blu_twilio_client import TwilioClient, TwilioSettings
            twilio = TwilioClient(TwilioSettings())
        body = _format_whatsapp_digest(tenant.get("nome_empresa", "Sua empresa"), insights)
        sid = twilio.send_whatsapp(to=phone, body=body)
        return bool(sid)
    except Exception:  # noqa: BLE001
        logger.exception("daily_insights: failed to send whatsapp digest for %s", client_id)
        return False


def _format_whatsapp_digest(empresa: str, insights: list[dict[str, Any]]) -> str:
    lines = [f"*Blu — Resumo diário ({empresa})*", ""]
    severity_emoji = {"error": "🔴", "warning": "🟠", "info": "🔵"}
    for i in insights[:5]:
        emoji = severity_emoji.get(i.get("severity", "info"), "🔵")
        lines.append(f"{emoji} *{i.get('title')}*")
        if i.get("observation"):
            lines.append(i["observation"])
        if i.get("recommendation"):
            lines.append(f"_→ {i['recommendation']}_")
        lines.append("")
    lines.append("Veja no painel: https://app.blu.com.br/")
    return "\n".join(lines).strip()


def _finalise(result: RoutineRunResult, start: datetime, db: Any | None, today: date) -> RoutineRunResult:
    result.duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
    if db is None:
        return result
    try:
        db.rpc(
            "record_audit",
            {
                "p_action":     "routine.daily_insights.run",
                "p_payload": {
                    "run_date": today.isoformat(),
                    "insights_returned": result.insights_returned,
                    "insights_written": result.insights_written,
                    "notification_sent": result.notification_sent,
                    "skipped": result.skipped,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                    **result.payload,
                },
                "p_resource":     "client_insights",
                "p_actor_kind":   "cron",
                "p_agent_slug":   "analytics",
                "p_outcome":      "failure" if result.error else ("success" if not result.skipped else "partial"),
                "p_client_id":    result.client_id,
            },
        ).execute()
    except Exception:  # noqa: BLE001
        logger.warning("daily_insights: failed to record audit log entry", exc_info=True)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> int:
    parser = argparse.ArgumentParser(description="Run the daily insights routine")
    parser.add_argument("--client-id", help="Run for a single tenant (UUID). Omit to run for all.")
    parser.add_argument("--period", default="30d")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--max-insights", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.client_id:
        result = asyncio.run(
            run_for_client(
                args.client_id,
                period=args.period,
                window_days=args.window_days,
                max_insights=args.max_insights,
            )
        )
        print(json.dumps(result.__dict__, default=str, indent=2))
        return 1 if result.error else 0

    results = asyncio.run(
        run_all_enabled(
            period=args.period,
            window_days=args.window_days,
            max_insights=args.max_insights,
            concurrency=args.concurrency,
        )
    )
    print(json.dumps([r.__dict__ for r in results], default=str, indent=2))
    return 1 if any(r.error for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
