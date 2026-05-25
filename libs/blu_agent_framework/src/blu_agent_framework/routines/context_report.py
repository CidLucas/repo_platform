"""
Context Report routine.

Pipeline (per tenant):

    1. Fetch all KPI metrics with trend data from
       analytics_v2.get_context_metrics_for_client().
    2. Build natural-language phrases per KPI (pure Python, deterministic).
    3. Fetch supporting data in parallel: active anomaly insights, data
       freshness from reg_jobs, and top-5 rankings from dimension tables.
    4. Render a Markdown report from a Jinja2 template.
    5. Upsert the report to Storage + vector DB (archive previous, upload,
       insert document row, invoke process-document Edge Function for chunking
       and embedding).  The report is searchable via RAG immediately after.
    6. Append a single audit_log entry summarising the run.

Trigger paths
─────────────
- CLI: `python -m blu_agent_framework.routines.context_report --client-id <uuid>`
- Nightly scheduler: runs after daily_insights (~03:15 local).

Design notes
────────────
- Synchronous: no LLM call here — phrases are built deterministically.
  Entry points are async-compatible for consistency with other routines.
- Service-role only: must read any tenant's data.
- The rendered Markdown is the canonical artifact stored in Storage.
  Everything downstream (vector DB, future UI cards) consumes this file.
- Metadata enrichment (Ollama) is skipped for context reports: we already
  know the category/theme, so per-chunk LLM classification adds no value.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dimension order and display labels
# ---------------------------------------------------------------------------

DIMENSION_ORDER: list[tuple[str, str]] = [
    ("financeiro", "Finanças"),
    ("clientes",   "Clientes"),
    ("compras",    "Compras"),
]

# Highest-value streak threshold: only mention streaks ≥ this length
_STREAK_MIN: int = 2

# KPIs surfaced in the Visão Geral summary block (ordered)
_SUMMARY_KPIS: list[str] = [
    "receita_liquida",
    "ticket_medio",
    "total_pedidos",
    "clientes_unicos",
    "taxa_recorrencia_perc",
    "fornecedores_ativos",
]

# Snapshot KPIs: current-state only, no monthly trend context available
_SNAPSHOT_KPIS: frozenset[str] = frozenset({
    "receita_ytd",
    "skus_total",
    "clientes_base_total",
    "clientes_ativos_90d",
    "recencia_media_dias",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MetricRow:
    """One row returned by analytics_v2.get_context_metrics_for_client."""

    dimension: str
    kpi: str
    label: str
    unit: str
    current_value: float | None
    prev_month_value: float | None
    avg_6m: float | None
    mom_pct: float | None
    vs_6m_avg_pct: float | None
    streak_months: int

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> MetricRow:
        return cls(
            dimension=row["dimension"],
            kpi=row["kpi"],
            label=row["label"],
            unit=row["unit"],
            current_value=_coerce(row.get("current_value")),
            prev_month_value=_coerce(row.get("prev_month_value")),
            avg_6m=_coerce(row.get("avg_6m")),
            mom_pct=_coerce(row.get("mom_pct")),
            vs_6m_avg_pct=_coerce(row.get("vs_6m_avg_pct")),
            streak_months=int(row.get("streak_months") or 0),
        )


@dataclass
class RoutineRunResult:
    client_id: str
    report_chars: int = 0
    metrics_count: int = 0
    upserted: bool = False
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
    db: Any | None = None,
    today: date | None = None,
    dry_run: bool = False,
) -> RoutineRunResult:
    """Run the context report pipeline for a single tenant."""

    start = datetime.now(UTC)
    today = today or start.date()
    result = RoutineRunResult(client_id=client_id)

    try:
        from blu_supabase_client import get_supabase_client

        db = db or get_supabase_client(use_service_role=True)

        tenant = _fetch_tenant(db, client_id)
        if tenant is None:
            result.skipped = "tenant_not_found"
            return _finalise(result, start, db, today)

        rows = _fetch_metrics(db, client_id)
        if not rows:
            result.skipped = "no_metrics_data"
            return _finalise(result, start, db, today)

        result.metrics_count = len(rows)
        result.payload["kpi_count"] = len(rows)

        insights  = _fetch_insights(db, client_id)
        freshness = _fetch_data_freshness(db, client_id)
        dim_totals = _fetch_dim_totals(db, client_id)
        top_lists = _fetch_top_lists(db, client_id, dim_totals)
        annual    = _fetch_annual_metrics(db, client_id)

        result.payload["insights_count"] = len(insights)
        result.payload["annual_years"]   = len(annual)

        sections = _build_phrases(rows, today)
        summary  = _build_summary(rows)
        markdown = _render_report(
            sections,
            tenant=tenant,
            today=today,
            summary=summary,
            insights=insights,
            freshness=freshness,
            top_lists=top_lists,
            annual=annual,
        )
        result.report_chars = len(markdown)
        result.payload["report_chars"] = result.report_chars

        if not dry_run:
            result.upserted = _upsert_to_vector_db(
                db, client_id=client_id, markdown=markdown, today=today
            )

        return _finalise(result, start, db, today)

    except Exception as exc:  # noqa: BLE001
        logger.exception("context_report run failed for %s", client_id)
        result.error = f"{type(exc).__name__}: {exc}"
        return _finalise(result, start, db, today)


async def run_all_enabled(
    *,
    db: Any | None = None,
    concurrency: int = 4,
    dry_run: bool = False,
) -> list[RoutineRunResult]:
    """Run the context report for every active tenant (all rows in clientes_blu)."""

    import asyncio

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
            return await run_for_client(client_id, db=db, dry_run=dry_run)

    return await asyncio.gather(*(_bound(t["client_id"]) for t in tenants))


# ---------------------------------------------------------------------------
# Step 1 — fetch tenant, metrics, and enrichment data
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
    return dict(rows[0]) if rows else None


def _fetch_metrics(db: Any, client_id: str) -> list[MetricRow]:
    try:
        resp = (
            db.schema("analytics_v2")
            .rpc("get_context_metrics_for_client", {"p_client_id": client_id})
            .execute()
        )
        return [MetricRow.from_dict(r) for r in (resp.data or [])]
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_context_metrics_for_client failed for %s: %s", client_id, exc)
        return []


def _fetch_insights(db: Any, client_id: str) -> list[dict[str, Any]]:
    """Fetch the most recent active anomaly insights produced by daily_insights."""
    try:
        resp = (
            db.table("client_insights")
            .select("room, title, body, severity, generated_at")
            .eq("client_id", client_id)
            .eq("dismissed", False)
            .order("generated_at", desc=True)
            .limit(6)
            .execute()
        )
        return resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch insights for %s: %s", client_id, exc)
        return []


def _fetch_data_freshness(db: Any, client_id: str) -> str | None:
    """Return ISO timestamp of the most recent completed sync job for this client."""
    try:
        resp = (
            db.schema("analytics_v2")
            .table("reg_jobs")
            .select("completed_at")
            .eq("client_id", client_id)
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows and rows[0].get("completed_at"):
            return rows[0]["completed_at"]
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch data freshness for %s: %s", client_id, exc)
        return None


def _fetch_dim_totals(db: Any, client_id: str) -> dict[str, float]:
    """Return total receita for each entity type — used to compute concentration share %."""
    try:
        resp = (
            db.schema("analytics_v2")
            .rpc("get_dim_totals_for_client", {"p_client_id": client_id})
            .execute()
        )
        return {
            row["entity"]: float(row["total_receita"] or 0)
            for row in (resp.data or [])
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch dim totals for %s: %s", client_id, exc)
        return {}


def _fetch_top_lists(
    db: Any, client_id: str, totals: dict[str, float]
) -> dict[str, list[dict[str, Any]]]:
    """Fetch top-5 clients, products, and suppliers by revenue; enrich with share %."""
    result: dict[str, list[dict[str, Any]]] = {
        "clients": [],
        "products": [],
        "suppliers": [],
    }

    try:
        resp = (
            db.schema("analytics_v2")
            .table("dim_clientes")
            .select("nome, receita_total, total_pedidos")
            .eq("client_id", client_id)
            .gt("receita_total", 0)
            .order("receita_total", desc=True)
            .limit(5)
            .execute()
        )
        total = totals.get("clients", 0)
        rows = resp.data or []
        for row in rows:
            rev = float(row.get("receita_total") or 0)
            row["share_perc"] = round(rev / total * 100, 1) if total > 0 else None
        result["clients"] = rows
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch top clients for %s: %s", client_id, exc)

    try:
        resp = (
            db.schema("analytics_v2")
            .table("dim_inventory")
            .select("nome, sku, receita_total, quantidade_total_vendida")
            .eq("client_id", client_id)
            .gt("receita_total", 0)
            .order("receita_total", desc=True)
            .limit(5)
            .execute()
        )
        total = totals.get("products", 0)
        rows = resp.data or []
        for row in rows:
            rev = float(row.get("receita_total") or 0)
            row["share_perc"] = round(rev / total * 100, 1) if total > 0 else None
        result["products"] = rows
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch top products for %s: %s", client_id, exc)

    try:
        resp = (
            db.schema("analytics_v2")
            .table("dim_fornecedores")
            .select("nome, receita_total, total_pedidos_recebidos")
            .eq("client_id", client_id)
            .gt("receita_total", 0)
            .order("receita_total", desc=True)
            .limit(5)
            .execute()
        )
        total = totals.get("suppliers", 0)
        rows = resp.data or []
        for row in rows:
            rev = float(row.get("receita_total") or 0)
            row["share_perc"] = round(rev / total * 100, 1) if total > 0 else None
        result["suppliers"] = rows
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch top suppliers for %s: %s", client_id, exc)

    return result


def _fetch_annual_metrics(db: Any, client_id: str) -> list[dict[str, Any]]:
    """Return one row per calendar year with aggregated business metrics and YoY growth."""
    try:
        resp = (
            db.schema("analytics_v2")
            .rpc("get_annual_metrics_for_client", {"p_client_id": client_id})
            .execute()
        )
        return resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch annual metrics for %s: %s", client_id, exc)
        return []


# ---------------------------------------------------------------------------
# Step 2 — build summary + phrases
# ---------------------------------------------------------------------------


def _build_summary(rows: list[MetricRow]) -> list[str]:
    """Extract headline metrics for the Visão Geral block."""
    kpi_map = {row.kpi: row for row in rows}
    lines: list[str] = []

    for slug in _SUMMARY_KPIS:
        row = kpi_map.get(slug)
        if row is None or row.current_value is None:
            continue
        line = f"**{row.label}**: {_fmt(row.current_value, row.unit)}"
        if row.mom_pct is not None:
            arrow = "▲" if row.mom_pct >= 0 else "▼"
            line += f" ({arrow}{_fmt_change(row.mom_pct, row.unit)} vs mês anterior)"
        lines.append(line)

    return lines


def _build_phrases(rows: list[MetricRow], today: date | None = None) -> dict[str, list[str]]:
    """Return {dimension: [phrase, ...]} for all KPIs that have data."""

    sections: dict[str, list[str]] = {dim: [] for dim, _ in DIMENSION_ORDER}
    kpi_map = {row.kpi: row for row in rows}

    for row in rows:
        if row.current_value is None:
            continue
        if row.kpi in _SNAPSHOT_KPIS:
            phrase = _build_snapshot_phrase(row, kpi_map, today)
        else:
            phrase = _build_phrase(row)
        bucket = sections.get(row.dimension)
        if bucket is not None:
            bucket.append(phrase)

    return sections


def _build_snapshot_phrase(
    row: MetricRow,
    kpi_map: dict[str, MetricRow],
    today: date | None,
) -> str:
    """Compose a contextualised phrase for a snapshot (current-state) KPI."""

    v = row.current_value
    assert v is not None  # caller guarantees

    if row.kpi == "receita_ytd":
        ref = today or date.today()
        months = ref.month - 1 or 1  # months fully elapsed
        period = f"jan–{_month_abbr(ref.month - 1)}/{ref.year}" if ref.month > 1 else f"jan/{ref.year}"
        return f"**{row.label}**: {_fmt(v, 'BRL')} acumulados em {months} meses ({period})"

    if row.kpi == "skus_total":
        ativos = kpi_map.get("skus_ativos")
        if ativos and ativos.current_value:
            pct = round(ativos.current_value / v * 100, 1) if v > 0 else 0
            return (
                f"**{row.label}**: {_fmt(v, 'count')} SKUs no catálogo"
                f" · {_fmt(ativos.current_value, 'count')} ativos este mês ({pct}% do catálogo)"
            )
        return f"**{row.label}**: {_fmt(v, 'count')} SKUs no catálogo"

    if row.kpi == "clientes_base_total":
        ativos = kpi_map.get("clientes_ativos_90d")
        if ativos and ativos.current_value and v > 0:
            pct = round(ativos.current_value / v * 100, 1)
            return (
                f"**{row.label}**: {_fmt(v, 'count')} clientes cadastrados"
                f" · {_fmt(ativos.current_value, 'count')} ativos nos últimos 90 dias ({pct}% da base)"
            )
        return f"**{row.label}**: {_fmt(v, 'count')} clientes cadastrados"

    if row.kpi == "clientes_ativos_90d":
        base = kpi_map.get("clientes_base_total")
        if base and base.current_value and base.current_value > 0:
            pct = round(v / base.current_value * 100, 1)
            return (
                f"**{row.label}**: {_fmt(v, 'count')} clientes"
                f" ({pct}% dos {_fmt(base.current_value, 'count')} cadastrados)"
            )
        return f"**{row.label}**: {_fmt(v, 'count')} clientes com compra nos últimos 90 dias"

    if row.kpi == "recencia_media_dias":
        if v <= 30:
            status = "base muito ativa"
        elif v <= 90:
            status = "base saudável"
        elif v <= 180:
            status = "base envelhecendo"
        elif v <= 365:
            status = "base com baixa frequência de retorno"
        else:
            status = "base com alto índice de abandono"
        return f"**{row.label}**: {_fmt(v, 'days')} em média — {status}"

    # fallback for any future snapshot KPIs
    return f"**{row.label}**: {_fmt(v, row.unit)}"


def _month_abbr(month: int) -> str:
    _ABBR = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    return _ABBR[(month - 1) % 12]


def _build_phrase(row: MetricRow) -> str:
    """Compose a natural-language sentence for a single trend KPI row."""

    current_str = _fmt(row.current_value, row.unit)
    parts: list[str] = []

    # ── Current value ────────────────────────────────────────────────────────
    parts.append(f"**{row.label}**: {current_str} este mês")

    # ── MoM comparison ───────────────────────────────────────────────────────
    if row.mom_pct is not None and row.prev_month_value is not None:
        prev_str = _fmt(row.prev_month_value, row.unit)
        change_str = _fmt_change(row.mom_pct, row.unit)
        arrow = "▲" if row.mom_pct >= 0 else "▼"
        parts.append(f"{arrow} {change_str} vs mês anterior ({prev_str})")
    elif row.prev_month_value is None:
        parts.append("primeiro mês com dados")

    # ── vs 6-month average ───────────────────────────────────────────────────
    if row.vs_6m_avg_pct is not None and row.avg_6m is not None:
        avg_str = _fmt(row.avg_6m, row.unit)
        direction = "acima" if row.vs_6m_avg_pct >= 0 else "abaixo"
        abs_pct = abs(row.vs_6m_avg_pct)
        if row.unit == "%":
            pp = abs(row.current_value - row.avg_6m) if row.current_value is not None else abs_pct
            parts.append(f"{pp:.1f} p.p. {direction} da média dos últimos 6 meses ({avg_str})")
        else:
            parts.append(f"{abs_pct:.1f}% {direction} da média dos últimos 6 meses ({avg_str})")

    # ── Streak ───────────────────────────────────────────────────────────────
    n = abs(row.streak_months)
    if n >= _STREAK_MIN:
        trend = "crescimento" if row.streak_months > 0 else "queda"
        parts.append(f"tendência de {trend} há {n} meses consecutivos")

    return " · ".join(parts)


# ---------------------------------------------------------------------------
# Value formatting helpers
# ---------------------------------------------------------------------------


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "N/D"
    if unit == "BRL":
        if value >= 1_000_000:
            return f"R$ {value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"R$ {value / 1_000:.0f}k"
        return f"R$ {value:.0f}"
    if unit == "%":
        return f"{value:.1f}%"
    if unit == "count":
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"{int(value):,}".replace(",", ".")
        return str(int(value))
    if unit == "days":
        return f"{int(value)} dias"
    return f"{value:.2f}"


def _fmt_change(mom_pct: float, unit: str) -> str:
    """Format a MoM change value.  % KPIs use p.p., others use relative %."""
    sign = "+" if mom_pct >= 0 else ""
    if unit == "%":
        return f"{sign}{mom_pct:.1f} p.p."
    return f"{sign}{mom_pct:.1f}%"


def _coerce(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Step 3 — render Markdown report
# ---------------------------------------------------------------------------

_REPORT_TEMPLATE = """\
# BLU Relatório de Contexto — {{ empresa }} ({{ tier }}) — {{ month_label }}

*Gerado em {{ generated_at }} · Referência: {{ data_ref }}{% if freshness %} · Última sincronização: {{ freshness }}{% endif %}*

---

## Visão Geral

{% if summary %}
{% for line in summary %}
- {{ line }}
{% endfor %}
{% else %}
*Sem dados de resumo disponíveis.*
{% endif %}

---
{% for dim_key, dim_label in dimensions %}
{% set section = sections[dim_key] %}
{% if section %}
## {{ dim_label }}

{% for phrase in section %}
- {{ phrase }}
{% endfor %}

{% endif %}
{% endfor %}
---
{% if annual %}
## Histórico Anual

| Ano | Receita | Pedidos | Clientes Únicos | Novos Clientes | Ticket Médio | Fornecedores | SKUs | vs Ano Anterior |
|-----|---------|---------|----------------|----------------|--------------|-------------|------|----------------|
{% for y in annual %}| {{ y.ano }}{% if y.is_partial %}*{% endif %} | {{ fmt(y.receita, 'BRL') }} | {{ fmt(y.total_pedidos, 'count') }} | {{ fmt(y.clientes_unicos, 'count') }} | {{ fmt(y.clientes_novos, 'count') }} | {{ fmt(y.ticket_medio, 'BRL') }} | {{ fmt(y.fornecedores_ativos, 'count') }} | {{ fmt(y.skus_ativos, 'count') }} | {% if y.yoy_receita_pct is not none %}{{ '+' if y.yoy_receita_pct >= 0 else '' }}{{ '%.1f'|format(y.yoy_receita_pct) }}%{% else %}—{% endif %} |
{% endfor %}
{% set partial = annual | selectattr('is_partial') | list %}
{% if partial %}
*Ano em curso (parcial). Projeção anualizada: {{ fmt(partial[0].receita_anualizada, 'BRL') if partial[0].receita_anualizada else 'N/D' }}.*
{% endif %}

{% endif %}
---
{% if top_lists.clients %}
## Top Clientes por Receita (acumulado)

| # | Cliente | Receita Total | Share | Pedidos |
|---|---------|--------------|-------|---------|
{% for c in top_lists.clients %}| {{ loop.index }} | {{ c.nome or 'N/D' }} | {{ fmt(c.receita_total, 'BRL') }} | {{ fmt_pct(c.share_perc) }} | {{ c.total_pedidos or 0 }} |
{% endfor %}

{% endif %}
{% if top_lists.products %}
## Top Produtos por Receita (acumulado)

| # | Produto | Receita Total | Share | Qtd. Vendida |
|---|---------|--------------|-------|-------------|
{% for p in top_lists.products %}| {{ loop.index }} | {{ p.nome or p.sku or 'N/D' }} | {{ fmt(p.receita_total, 'BRL') }} | {{ fmt_pct(p.share_perc) }} | {{ fmt(p.quantidade_total_vendida, 'count') }} |
{% endfor %}

{% endif %}
{% if top_lists.suppliers %}
## Top Fornecedores por Receita (acumulado)

| # | Fornecedor | Receita Total | Share | Pedidos Recebidos |
|---|-----------|--------------|-------|------------------|
{% for s in top_lists.suppliers %}| {{ loop.index }} | {{ s.nome or 'N/D' }} | {{ fmt(s.receita_total, 'BRL') }} | {{ fmt_pct(s.share_perc) }} | {{ s.total_pedidos_recebidos or 0 }} |
{% endfor %}

{% endif %}
{% if insights %}
---

## Alertas e Anomalias Detectadas

{% for ins in insights %}
- **[{{ ins.severity | upper }}] {{ ins.title }}** *({{ ins.dimension }})*: {{ ins.body }}
{% endfor %}

{% endif %}
---
*Este documento é gerado automaticamente pela Blu e atualizado diariamente.*
"""


def _fmt_pct(value: float | None) -> str:
    return f"{value:.1f}%" if value is not None else "N/D"


def _render_report(
    sections: dict[str, list[str]],
    *,
    tenant: dict[str, Any],
    today: date,
    summary: list[str],
    insights: list[dict[str, Any]],
    freshness: str | None,
    top_lists: dict[str, list[dict[str, Any]]],
    annual: list[dict[str, Any]],
) -> str:
    try:
        from jinja2 import Environment
    except ImportError as exc:
        raise RuntimeError(
            "jinja2 is required for context_report — add it to pyproject.toml"
        ) from exc

    env = Environment(autoescape=False, keep_trailing_newline=True)
    template = env.from_string(_REPORT_TEMPLATE)

    freshness_fmt: str | None = None
    if freshness:
        try:
            dt = datetime.fromisoformat(freshness.replace("Z", "+00:00"))
            freshness_fmt = dt.strftime("%d/%m/%Y %H:%M UTC")
        except Exception:  # noqa: BLE001
            freshness_fmt = freshness

    return template.render(
        empresa=tenant.get("nome_empresa", "Empresa"),
        tier=tenant.get("tier", "BASIC"),
        month_label=today.strftime("%B %Y"),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        data_ref=today.strftime("%d/%m/%Y"),
        freshness=freshness_fmt,
        dimensions=DIMENSION_ORDER,
        sections=sections,
        summary=summary,
        insights=insights,
        top_lists=top_lists,
        annual=annual,
        fmt=_fmt,
        fmt_pct=_fmt_pct,
    )


# ---------------------------------------------------------------------------
# Step 4 — vector DB upsert
# ---------------------------------------------------------------------------


def _upsert_to_vector_db(
    db: Any,
    *,
    client_id: str,
    markdown: str,
    today: date,
) -> bool:
    """Upload the report to Storage + vector DB for RAG retrieval.

    Steps:
        1. Archive existing generated report for this client (keep history,
           exclude from active RAG search).
        2. Upload markdown bytes to Supabase Storage (upsert).
        3. INSERT a new row into vector_db.documents (status='pending').
        4. POST to the process-document Edge Function (synchronous) — chunks,
           embeds, and inserts into vector_db.document_chunks.

    Returns True if the edge function completed successfully, False otherwise.
    Failures are logged but not raised so the audit entry is always written.
    """
    import os

    import httpx

    year_month = today.strftime("%Y-%m")
    file_name = f"context-report-{year_month}.md"
    storage_path = f"{client_id}/{file_name}"

    # ── 1. Archive previous generated report (only completed/pending) ─────────
    try:
        db.schema("vector_db").table("documents").update({"source": "archived"}).eq(
            "client_id", client_id
        ).eq("source", "generated").eq("category", "business_context").in_(
            "status", ["pending", "completed"]
        ).execute()
        logger.debug("context_report: archived previous context report for %s", client_id)
    except Exception:
        logger.warning(
            "context_report: could not archive previous document for %s",
            client_id,
            exc_info=True,
        )

    # ── 2. Upload markdown to Supabase Storage ────────────────────────────────
    raw = markdown.encode("utf-8")
    db.storage.from_("knowledge-base").upload(
        storage_path,
        raw,
        file_options={"content-type": "text/markdown; charset=utf-8", "upsert": "true"},
    )
    logger.debug("context_report: uploaded %d bytes to %s", len(raw), storage_path)

    # ── 3. Insert document row ────────────────────────────────────────────────
    resp = (
        db.schema("vector_db")
        .table("documents")
        .insert({
            "client_id":    client_id,
            "title":        f"Relatório de Contexto — {year_month}",
            "file_name":    file_name,
            "file_type":    "md",
            "storage_path": storage_path,
            "source":       "generated",
            "scope":        "client",
            "category":     "business_context",
            "status":       "pending",
        })
        .execute()
    )
    document_id: str = resp.data[0]["id"]
    logger.debug("context_report: inserted document row %s", document_id)

    # ── 4. Invoke process-document Edge Function (synchronous) ────────────────
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key  = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # Edge functions with verify_jwt=true require a JWT Bearer token.
    # The new sb_secret_* key format is not a JWT, so fall back to the anon
    # JWT.  The function uses its own SUPABASE_SERVICE_ROLE_KEY env var for
    # internal DB operations, so anon auth is sufficient to pass the gate.
    anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    bearer   = service_key if service_key.startswith("eyJ") else anon_key

    fn_resp = httpx.post(
        f"{supabase_url}/functions/v1/process-document",
        json={
            "document_id":   document_id,
            "storage_path":  storage_path,
            "client_id":     client_id,
            "file_name":     file_name,
            "file_type":     "md",
            # Expanded report (~2x previous size). 300 tokens/chunk keeps
            # chunk count within Edge Function memory limits (~5-7 chunks).
            "target_tokens":            300,
            # Per-chunk Ollama enrichment adds no value here: every chunk is
            # business_context by definition. Skip to save memory + time.
            "skip_metadata_enrichment": True,
        },
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type":  "application/json",
        },
        timeout=120.0,
    )

    if fn_resp.status_code != 200:
        raise RuntimeError(
            f"process-document returned {fn_resp.status_code}: {fn_resp.text}"
        )

    result = fn_resp.json()
    completed = result.get("status") == "completed"
    logger.info(
        "context_report: process-document finished for %s — status=%s chunks=%s",
        client_id, result.get("status"), result.get("chunk_count"),
    )

    # Tag chunks with filtering metadata so RAG queries can narrow by type/date.
    if completed:
        try:
            db.schema("vector_db").table("document_chunks").update({
                "at_date":          today.replace(day=1).isoformat(),
                "document_type_id": "context_report",
                "is_current":       True,
                "language":         "pt-BR",
            }).eq("document_id", document_id).execute()
            logger.debug("context_report: tagged chunks for document %s", document_id)
        except Exception:
            logger.warning(
                "context_report: could not tag chunks for %s", document_id, exc_info=True
            )

    return completed


# ---------------------------------------------------------------------------
# Step 5 — audit log
# ---------------------------------------------------------------------------


def _finalise(
    result: RoutineRunResult,
    start: datetime,
    db: Any | None,
    today: date,
) -> RoutineRunResult:
    result.duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
    if db is None:
        return result
    try:
        db.rpc(
            "record_audit",
            {
                "p_action":      "routine.context_report.run",
                "p_entity_type": "context_report",
                "p_entity_id":   result.client_id,
                "p_payload": {
                    "run_date":      today.isoformat(),
                    "metrics_count": result.metrics_count,
                    "report_chars":  result.report_chars,
                    "upserted":      result.upserted,
                    "skipped":       result.skipped,
                    "error":         result.error,
                    "duration_ms":   result.duration_ms,
                    **result.payload,
                },
            },
        ).execute()
    except Exception:  # noqa: BLE001
        logger.warning("context_report: failed to record audit log entry", exc_info=True)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> int:
    import asyncio

    parser = argparse.ArgumentParser(description="Run the context report routine")
    parser.add_argument("--client-id", help="Run for a single tenant (UUID). Omit to run for all.")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true", help="Build report but skip vector DB upsert")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.client_id:
        result = asyncio.run(
            run_for_client(args.client_id, dry_run=args.dry_run)
        )
        print(json.dumps(result.__dict__, default=str, indent=2))
        return 1 if result.error else 0

    results = asyncio.run(
        run_all_enabled(concurrency=args.concurrency, dry_run=args.dry_run)
    )
    print(json.dumps([r.__dict__ for r in results], default=str, indent=2))
    return 1 if any(r.error for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
