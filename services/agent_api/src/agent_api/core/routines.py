"""
Routine execution engine.

Picks up already-claimed routine executions, dispatches each step to the
correct engine (function | skill | artifact | legacy), carries outputs in a
shared state dict between steps, and notifies the client on completion.

Step types
──────────
  function  — deterministic call: no LLM, calls routine_functions registry
  skill     — LangGraph specialist subgraph via AgentBuilder.use_specialist_graph();
              structured output extracted from result_state or text fallback
  artifact  — side-effectful emit: email, alert, stored document
  (none)    — legacy format {step, agent, action, output}: routed to _invoke_worker
              unchanged for backward compatibility

State machine
─────────────
Each step's outputs merge into a shared `state` dict that persists across the
entire execution. Template strings in step inputs/task_template are resolved
against state with {{key}} syntax before the step runs. State is checkpointed
to client_routine_executions.result_metadata after every step so progress
survives restarts or monitoring.

Concurrency guard
─────────────────
MCP manager's set_client_id() is stateful — the semaphore ensures only one
client's routine runs at a time within a single worker process.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from blu_supabase_client import get_supabase_client

if TYPE_CHECKING:
    from blu_context_service import ContextService

logger = logging.getLogger(__name__)


# P0: tempo máximo total de uma execução de rotina (segundos)
_ROUTINE_EXECUTION_TIMEOUT_S = 120

# P1: semáforo por cliente — max 2 execuções simultâneas por client_id
_client_semaphores: dict[str, asyncio.Semaphore] = {}
_client_semaphores_lock = asyncio.Lock()

# P1: circuit breaker — falhas consecutivas antes de suspender rotina
_CIRCUIT_BREAKER_MAX_FAILURES = 3

# Marker appended to result_text when a routine pauses for HITL approval
_AWAITING_APPROVAL_MARKER = "__awaiting_approval__"


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_custom_routine(routine_id: str) -> bool:
    return bool(_UUID_RE.match(routine_id))


# ---------------------------------------------------------------------------
# Template resolver
# ---------------------------------------------------------------------------


_PURE_PLACEHOLDER_RE = re.compile(r"^\{\{\s*(\w+)\s*\}\}$")
_INLINE_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _resolve_templates(obj: Any, state: dict[str, Any]) -> Any:
    """
    Recursively resolve {{key}} placeholders in strings/dicts/lists.

    Pure-placeholder strings like "{{client_list}}" are replaced with the
    raw state value — preserving its type (list, dict, int, …) so downstream
    function steps receive the correct Python object rather than a JSON string.

    Mixed strings like "Hello {{nome_empresa}}!" are interpolated normally;
    dict/list values are JSON-serialised in that context.

    Non-string leaves are returned as-is.
    """
    if isinstance(obj, str):
        # Pure placeholder — preserve the value's original type
        m = _PURE_PLACEHOLDER_RE.match(obj)
        if m:
            key = m.group(1)
            val = state.get(key)
            return obj if val is None else val

        # Mixed string — stringify everything
        def _replace(m: re.Match) -> str:
            key = m.group(1).strip()
            val = state.get(key)
            if val is None:
                return m.group(0)  # keep placeholder intact if key missing
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)
        return _INLINE_PLACEHOLDER_RE.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _resolve_templates(v, state) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_templates(v, state) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# JSON extraction helper (Phase 3 skill outputs — replaced by tool_use in Phase 4)
# ---------------------------------------------------------------------------


def _extract_json_from_text(text: str, outputs_schema: dict | None = None) -> dict | None:
    """
    Try to extract a JSON object or array from LLM response text.
    Looks for ```json ... ``` blocks first, then bare {/[ spans.
    When the LLM returns a JSON array and outputs_schema has exactly one key,
    the array is wrapped under that key.
    """
    # 1. Try fenced JSON block
    block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = block.group(1) if block else None

    # 2. Try raw {/[ span
    if not candidate:
        raw = re.search(r"(\{[\s\S]+\}|\[[\s\S]+\])", text)
        candidate = raw.group(0) if raw else None

    if not candidate:
        return None

    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(parsed, dict):
        return parsed

    if isinstance(parsed, list):
        # Wrap array under the first schema key if unambiguous
        if outputs_schema and len(outputs_schema) == 1:
            key = next(iter(outputs_schema))
            return {key: parsed}
        return None

    return None


# ---------------------------------------------------------------------------
# DB helpers (sync, run via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _claim_sync(batch_size: int) -> list[dict]:
    return (
        get_supabase_client()
        .rpc("claim_routine_executions", {"p_batch_size": batch_size})
        .execute()
        .data or []
    )


def _has_pending_approvals_sync(execution_id: str) -> bool:
    resp = (
        get_supabase_client()
        .table("approval_requests")
        .select("id")
        .eq("status", "pending")
        .filter("payload->>execution_id", "eq", execution_id)
        .execute()
    )
    return bool(resp.data)


def _fetch_routine_sync(routine_id: str) -> dict | None:
    db = get_supabase_client()
    if db is None:
        return None
    table = "client_routines" if _is_custom_routine(routine_id) else "cross_agent_routines"
    try:
        response = (
            db.table(table)
            .select("name, steps, config_schema")
            .eq("id", routine_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None
    except Exception:
        return None


def _fetch_client_routine_config_sync(client_id: str, routine_id: str) -> dict | None:
    db = get_supabase_client()
    if db is None:
        return None
    try:
        response = (
            db.table("client_routines")
            .select("notify_channel, config, name")
            .eq("client_id", client_id)
            .eq("routine_id", routine_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None
    except Exception:
        return None


def _update_execution_sync(execution_id: str, payload: dict) -> None:
    get_supabase_client().table("client_routine_executions").update(payload).eq(
        "id", execution_id
    ).execute()


def _heartbeat_sync(execution_id: str) -> None:
    """P1: atualiza heartbeat_at para indicar que a execução ainda está viva."""
    get_supabase_client().table("client_routine_executions").update(
        {"heartbeat_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", execution_id).execute()


def _record_routine_failure_sync(client_id: str, routine_id: str) -> str:
    """P1: incrementa falhas consecutivas; suspende se >= max. Retorna novo status."""
    resp = (
        get_supabase_client()
        .rpc(
            "record_routine_failure",
            {
                "p_client_id": client_id,
                "p_routine_id": routine_id,
                "p_max_failures": _CIRCUIT_BREAKER_MAX_FAILURES,
            },
        )
        .execute()
    )
    return resp.data or "active"


def _reset_routine_failures_sync(client_id: str, routine_id: str) -> None:
    """P1: reset circuit breaker após execução bem-sucedida."""
    get_supabase_client().rpc(
        "reset_routine_failures",
        {"p_client_id": client_id, "p_routine_id": routine_id},
    ).execute()


def _serialisable(state: dict) -> dict:
    """Return a JSON-serialisable subset of state (drop non-serialisable values)."""
    safe: dict = {}
    for k, v in state.items():
        try:
            json.dumps(v)
            safe[k] = v
        except (TypeError, ValueError):
            safe[k] = str(v)
    return safe


# ---------------------------------------------------------------------------
# Trigger system — DB helpers (sync)
# ---------------------------------------------------------------------------


def _fetch_triggered_routines_sync(trigger_type: str | list[str]) -> list[dict]:
    """Fetch catalog routines with the given trigger_type(s).

    Accepts a single value or a list. The builder/UI persist schedule-based
    routines as trigger_type='schedule' (see routines_router.py triggers list
    and routine-builder edge fn), while the seed catalog uses 'cron' — both
    mean the same cron-driven poll, so the cron check queries both.
    """
    types = [trigger_type] if isinstance(trigger_type, str) else list(trigger_type)
    try:
        return (
            get_supabase_client()
            .table("cross_agent_routines")
            .select("id, name, trigger_config")
            .in_("trigger_type", types)
            .execute()
            .data or []
        )
    except Exception as exc:
        logger.warning("[TriggerPoller] failed to fetch %s routines: %s", types, exc)
        return []


def _fetch_active_client_routines_sync(routine_id: str) -> list[dict]:
    """Fetch all client_routines subscriptions that are active for a catalog routine."""
    return (
        get_supabase_client()
        .table("client_routines")
        .select("id, client_id, trigger_config, config, last_run_at")
        .eq("routine_id", routine_id)
        .eq("active", True)
        .eq("status", "active")
        .execute()
        .data or []
    )


def _dispatch_execution_sync(
    client_id: str,
    routine_id: str,
    triggered_by: str,
    trigger_data: dict,
) -> str | None:
    """
    Insert a routine execution directly as 'dispatched', bypassing the
    SQL approval flow (which is for the legacy model).
    Also stamps last_run_at on the client_routines row so the cron poller
    doesn't re-fire until the next scheduled interval.
    Returns the new execution id, or None if a guard condition blocked it.
    """
    db = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Guard: skip if an execution is already in-flight for this routine+client
    in_flight = (
        db.table("client_routine_executions")
        .select("id")
        .eq("client_id", client_id)
        .eq("routine_id", routine_id)
        .in_("status", ["pending", "dispatched", "executing"])
        .limit(1)
        .execute()
        .data
    )
    if in_flight:
        return None

    resp = (
        db.table("client_routine_executions")
        .insert({
            "client_id": client_id,
            "routine_id": routine_id,
            "triggered_by": triggered_by,
            "trigger_data": trigger_data,
            "status": "dispatched",
            "dispatched_at": now_iso,
        })
        .execute()
    )
    exec_id = resp.data[0]["id"] if resp.data else None

    if exec_id:
        # Stamp last_run_at so the poller won't re-fire until next interval
        db.table("client_routines").update({"last_run_at": now_iso}).eq(
            "client_id", client_id
        ).eq("routine_id", routine_id).execute()

    return exec_id


def _stamp_last_run_sync(client_routine_id: str) -> None:
    """Set last_run_at = now on a client_routines row (by primary key)."""
    get_supabase_client().table("client_routines").update(
        {"last_run_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", client_routine_id).execute()


def _get_new_clients_rate_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """
    Return (current_month_count, avg_monthly_count) for new client acquisition.
    Uses dim_clientes.dias_recencia as a proxy: new clients have low recency.
    Raises on failure so the caller can skip this client rather than false-positive.
    """
    db = get_supabase_client(use_service_role=True)
    resp = db.rpc(
        "get_new_clients_monthly_rate",
        {"p_client_id": client_id, "p_window_months": window_months},
    ).execute()
    row = (resp.data or [{}])[0]
    return float(row.get("current_month_count", 0)), float(row.get("avg_monthly_count", 0))


# ---------------------------------------------------------------------------
# Numeric metric registry — pluggable metric resolvers
# ---------------------------------------------------------------------------
#
# Each entry maps a metric name to an async callable with signature:
#   resolver(client_id: str, cfg: dict) -> tuple[float, float]
#   returns (current_value, baseline_value)
#
# The trigger fires when: current_value < threshold * baseline_value
# (i.e. current is below threshold fraction of baseline — e.g. 0.85 = drop >15%)
#
# To add a new metric:
#   1. Implement _resolve_<metric>_sync(client_id, window_months) -> (current, baseline)
#   2. Register it in _NUMERIC_METRIC_REGISTRY below.
#
# trigger_config fields used by the engine (same for all metrics):
#   metric          — metric name (key in this registry)
#   threshold       — fraction of baseline that triggers (default 0.5; e.g. 0.85 for -15%)
#   window_months   — lookback window for baseline calculation (default 1)
#   cooldown_hours  — minimum hours between fires (default 24)


def _resolve_new_clients_rate_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """current month new clients vs avg of previous window_months."""
    db = get_supabase_client(use_service_role=True)
    resp = db.rpc(
        "get_new_clients_monthly_rate",
        {"p_client_id": client_id, "p_window_months": window_months},
    ).execute()
    row = (resp.data or [{}])[0]
    return float(row.get("current_month_count", 0)), float(row.get("avg_monthly_count", 0))


def _resolve_revenue_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """
    Current month gross revenue vs average of previous window_months.
    Uses faturamento_mensal or falls back to sum of fact_pedidos for the client.
    Raises on failure so the caller can skip this client rather than false-positive.
    """
    db = get_supabase_client(use_service_role=True)
    resp = db.rpc(
        "get_revenue_monthly_rate",
        {"p_client_id": client_id, "p_window_months": window_months},
    ).execute()
    row = (resp.data or [{}])[0]
    return float(row.get("current_month_revenue", 0)), float(row.get("avg_monthly_revenue", 0))


def _resolve_ticket_medio_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """Current month average ticket vs historical avg over window_months."""
    db = get_supabase_client(use_service_role=True)
    resp = db.rpc(
        "get_ticket_medio_monthly_rate",
        {"p_client_id": client_id, "p_window_months": window_months},
    ).execute()
    row = (resp.data or [{}])[0]
    return float(row.get("current_ticket", 0)), float(row.get("avg_ticket", 0))


def _resolve_churn_rate_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """
    Current month churn rate vs historical avg over window_months.
    NOTE: for churn, the trigger fires when current > threshold * baseline
    (spike, not drop). The engine always evaluates current < threshold * baseline,
    so set threshold > 1 (e.g. 1.5 = 50% above baseline) for spike detection.
    """
    db = get_supabase_client(use_service_role=True)
    resp = db.rpc(
        "get_churn_rate_monthly",
        {"p_client_id": client_id, "p_window_months": window_months},
    ).execute()
    row = (resp.data or [{}])[0]
    return float(row.get("current_churn_rate", 0)), float(row.get("avg_churn_rate", 0))


def _resolve_pedidos_count_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """Current month order count vs avg over window_months."""
    db = get_supabase_client(use_service_role=True)
    resp = db.rpc(
        "get_pedidos_monthly_rate",
        {"p_client_id": client_id, "p_window_months": window_months},
    ).execute()
    row = (resp.data or [{}])[0]
    return float(row.get("current_pedidos", 0)), float(row.get("avg_pedidos", 0))


def _resolve_saldo_conta_corrente_sync(client_id: str, window_months: int) -> tuple[float, float]:
    """
    Current checking-account balance vs configured threshold (absolute value comparison).

    Returns (saldo_cc, 1.0) so the engine evaluates: saldo_cc < threshold * 1.0
    i.e. the client sets threshold = minimum acceptable balance in BRL (e.g. 5000).
    Delegates to routine_functions._fetch_saldo_cc_sync — single source of truth for
    polp_accounts parsing. window_months is ignored (balance is point-in-time).
    """
    from agent_api.core.routine_functions import _fetch_saldo_cc_sync
    return _fetch_saldo_cc_sync(client_id), 1.0


# Registry: metric_name → sync resolver function
# Signature: (client_id: str, window_months: int) -> tuple[float, float]
_NUMERIC_METRIC_REGISTRY: dict[str, Any] = {
    "new_clients_monthly_rate": _resolve_new_clients_rate_sync,
    "revenue":                  _resolve_revenue_sync,
    "faturamento":              _resolve_revenue_sync,   # alias PT
    "ticket_medio":             _resolve_ticket_medio_sync,
    "churn_rate":               _resolve_churn_rate_sync,
    "pedidos_count":            _resolve_pedidos_count_sync,
    "saldo_conta_corrente":     _resolve_saldo_conta_corrente_sync,  # absolute threshold — polp_accounts
}


def list_numeric_metrics() -> list[dict]:
    """Return available metric names and labels for the UI config schema."""
    return [
        {"value": "revenue",                "label": "Faturamento mensal"},
        {"value": "new_clients_monthly_rate","label": "Novos clientes / mês"},
        {"value": "ticket_medio",           "label": "Ticket médio"},
        {"value": "pedidos_count",          "label": "Volume de pedidos"},
        {"value": "churn_rate",             "label": "Taxa de churn"},
        {"value": "saldo_conta_corrente",   "label": "Saldo em conta corrente (R$)"},
    ]


# ---------------------------------------------------------------------------
# Trigger system — async pollers
# ---------------------------------------------------------------------------


async def _check_cron_routines() -> int:
    """
    Evaluate all cron-triggered catalog routines.
    Enqueues a dispatched execution for each client whose schedule is due.
    """
    try:
        from croniter import croniter  # type: ignore[import]
    except ImportError:
        logger.warning("[TriggerPoller] croniter not installed — cron triggers disabled")
        return 0

    routines = await asyncio.to_thread(_fetch_triggered_routines_sync, ["cron", "schedule"])
    if not routines:
        return 0

    count = 0
    now = datetime.now(timezone.utc)

    for routine in routines:
        routine_id: str = routine["id"]
        default_expr: str = (routine.get("trigger_config") or {}).get("expression", "")

        client_rows = await asyncio.to_thread(_fetch_active_client_routines_sync, routine_id)
        for cr in client_rows:
            expr: str = (cr.get("trigger_config") or {}).get("expression") or default_expr
            if not expr:
                continue

            raw_last = cr.get("last_run_at")
            if not raw_last:
                # First enable: stamp last_run_at = now so the next fire happens at
                # the proper next interval rather than immediately.
                await asyncio.to_thread(_stamp_last_run_sync, cr["id"])
                continue

            last_dt = datetime.fromisoformat(raw_last.replace("Z", "+00:00"))
            try:
                next_run = croniter(expr, last_dt).get_next(datetime)
            except Exception:
                logger.warning("[TriggerPoller] invalid cron '%s' for routine %s", expr, routine_id)
                continue

            if next_run > now:
                continue  # not due yet

            exec_id = await asyncio.to_thread(
                _dispatch_execution_sync,
                str(cr["client_id"]),
                routine_id,
                "cron",
                {"expression": expr},
            )
            if exec_id:
                logger.info(
                    "[TriggerPoller] cron: routine=%s client=%s exec=%s",
                    routine_id, cr["client_id"], exec_id,
                )
                count += 1

    return count


async def _check_numeric_triggers() -> int:
    """
    Evaluate all numeric-triggered catalog routines against per-client metrics.

    Uses _NUMERIC_METRIC_REGISTRY so any registered metric can trigger a routine.
    trigger_config fields:
      metric        — key in _NUMERIC_METRIC_REGISTRY
      threshold     — fraction of baseline that fires (e.g. 0.85 = fires when current < 85% of avg)
      window_months — lookback for baseline (default 1)
      cooldown_hours— minimum hours between fires (default 24)
    """
    routines = await asyncio.to_thread(_fetch_triggered_routines_sync, "numeric")
    if not routines:
        return 0

    count = 0
    for routine in routines:
        routine_id: str = routine["id"]
        cfg: dict = routine.get("trigger_config") or {}
        metric: str = cfg.get("metric", "")
        threshold: float = float(cfg.get("threshold", 0.5))
        window_months: int = int(cfg.get("window_months", 1))
        cooldown_hours: int = int(cfg.get("cooldown_hours", 24))

        resolver = _NUMERIC_METRIC_REGISTRY.get(metric)
        if not resolver:
            logger.debug(
                "[TriggerPoller] unsupported metric '%s' — add it to _NUMERIC_METRIC_REGISTRY",
                metric,
            )
            continue

        client_rows = await asyncio.to_thread(_fetch_active_client_routines_sync, routine_id)
        now_num = datetime.now(timezone.utc)
        for cr in client_rows:
            client_id = str(cr["client_id"])

            # Per-client config overrides
            cr_config: dict = cr.get("config") or {}
            effective_threshold = float(cr_config.get("threshold", threshold))
            effective_window = int(cr_config.get("window_months", window_months))

            # Cooldown: skip if already fired within cooldown_hours
            raw_last = cr.get("last_run_at")
            if raw_last:
                last_dt = datetime.fromisoformat(raw_last.replace("Z", "+00:00"))
                if (now_num - last_dt).total_seconds() < cooldown_hours * 3600:
                    continue

            try:
                current, baseline = await asyncio.to_thread(
                    resolver, client_id, effective_window
                )
                if baseline == 0 or current >= effective_threshold * baseline:
                    continue  # condition not met or no data

                exec_id = await asyncio.to_thread(
                    _dispatch_execution_sync,
                    client_id,
                    routine_id,
                    "numeric",
                    {
                        "metric": metric,
                        "current_value": current,
                        "baseline_value": baseline,
                        "threshold": effective_threshold,
                        "drop_pct": round((1 - current / baseline) * 100, 1) if baseline else None,
                    },
                )
                if exec_id:
                    logger.info(
                        "[TriggerPoller] numeric: routine=%s client=%s metric=%s "
                        "current=%.2f baseline=%.2f threshold=%.2f exec=%s",
                        routine_id, client_id, metric, current, baseline, effective_threshold, exec_id,
                    )
                    count += 1
            except Exception as exc:
                logger.warning(
                    "[TriggerPoller] numeric eval failed for client=%s metric=%s: %s",
                    client_id, metric, exc,
                )

    return count


async def check_and_enqueue_triggers() -> int:
    """
    Poll all automatic triggers (cron + numeric) and enqueue due executions.
    Called once per dispatcher tick before the claim loop.
    Returns total number of executions enqueued.
    """
    try:
        cron_count = await _check_cron_routines()
        numeric_count = await _check_numeric_triggers()
        total = cron_count + numeric_count
        if total:
            logger.info("[TriggerPoller] enqueued %d execution(s) (cron=%d numeric=%d)", total, cron_count, numeric_count)
        return total
    except Exception:
        logger.exception("[TriggerPoller] trigger check failed")
        return 0


async def enqueue_routine_event(
    routine_id: str,
    client_id: str,
    trigger_data: dict | None = None,
) -> str | None:
    """
    Enqueue a catalog routine execution for an event trigger (e.g. onboarding_complete).
    Called from event hooks in the application layer.
    Returns the execution id, or None if guarded (in-flight, inactive).
    """
    exec_id = await asyncio.to_thread(
        _dispatch_execution_sync,
        client_id,
        routine_id,
        "event",
        trigger_data or {},
    )
    if exec_id:
        logger.info("[RoutineEvent] enqueued routine=%s client=%s exec=%s", routine_id, client_id, exec_id)
    return exec_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def claim_dispatched_batch(batch_size: int = 10) -> list[dict]:
    return await asyncio.to_thread(_claim_sync, batch_size)


async def _get_client_semaphore(client_id: str) -> asyncio.Semaphore:
    """P1: retorna semáforo por cliente (max 4 paralelos). Cria se não existir."""
    async with _client_semaphores_lock:
        if client_id not in _client_semaphores:
            _client_semaphores[client_id] = asyncio.Semaphore(4)
        return _client_semaphores[client_id]


async def _execute_one_with_heartbeat(
    exec_id: str,
    execution: dict,
    context_service: ContextService,
) -> tuple[str, str]:
    """P1: heartbeat em thread daemon (imune a event loop blocking).

    Se o event loop estiver bloqueado por chamada síncrona dentro de _execute_one,
    um heartbeat baseado em asyncio.sleep NUNCA acorda — foi o que causou o bug
    do reaper matando execuções legítimas. Threading.Thread + threading.Event.wait
    rodam fora do loop e continuam pulsando.
    """

    stop_event = threading.Event()

    def _heartbeat_thread() -> None:
        # Pulsa imediatamente para marcar início, depois a cada 20s.
        try:
            _heartbeat_sync(exec_id)
        except Exception:  # pragma: no cover
            logger.exception("[Heartbeat] initial pulse failed for %s", exec_id)
        while not stop_event.wait(20):
            try:
                _heartbeat_sync(exec_id)
                logger.debug("[Heartbeat] exec %s still alive", exec_id)
            except Exception:  # pragma: no cover
                logger.exception("[Heartbeat] pulse failed for %s", exec_id)

    hb = threading.Thread(
        target=_heartbeat_thread,
        name=f"heartbeat-{exec_id[:8]}",
        daemon=True,
    )
    hb.start()
    try:
        return await _execute_one(execution, context_service)
    finally:
        stop_event.set()
        hb.join(timeout=5)


async def _run_single_execution(
    execution: dict, context_service: ContextService
) -> None:
    """Executa uma única rotina com semáforo, heartbeat, timeout e circuit breaker."""
    exec_id    = str(execution["id"])
    client_id  = str(execution["client_id"])
    routine_id = str(execution["routine_id"])

    # P1: semáforo por cliente — evita que um cliente ocupe todos os workers
    client_sem = await _get_client_semaphore(client_id)

    try:
        async with client_sem:
            from agent_api.core.factory import get_mcp_manager
            get_mcp_manager().set_client_id(client_id)

            result_text, worker_slug = await asyncio.wait_for(
                _execute_one_with_heartbeat(exec_id, execution, context_service),
                timeout=_ROUTINE_EXECUTION_TIMEOUT_S,
            )
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {
                "status": "completed",
                "result_text": result_text,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "worker_slug": worker_slug,
            },
        )
    except asyncio.TimeoutError:
        logger.error(
            "[RoutineExecutor] Execution %s timed out after %ds",
            exec_id, _ROUTINE_EXECUTION_TIMEOUT_S,
            extra={
                "execution_id": exec_id,
                "routine_id": routine_id,
                "client_id": client_id,
                "error_type": "timeout",
            },
        )
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {
                "status": "failed",
                "result_text": f"Erro: timeout após {_ROUTINE_EXECUTION_TIMEOUT_S}s",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        new_status = await asyncio.to_thread(
            _record_routine_failure_sync, client_id, routine_id
        )
        if new_status == "suspended":
            logger.warning(
                "[CircuitBreaker] routine %s client %s SUSPENDED after repeated failures",
                routine_id, client_id,
            )
        return

    except asyncio.CancelledError:
        logger.error("[RoutineExecutor] Execution %s was cancelled mid-run", exec_id)
        raise

    except Exception as exc:
        logger.exception("[RoutineExecutor] Execution %s failed", exec_id)
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {
                "status": "failed",
                "result_text": f"Erro: {exc}",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        new_status = await asyncio.to_thread(
            _record_routine_failure_sync, client_id, routine_id
        )
        if new_status == "suspended":
            logger.warning(
                "[CircuitBreaker] routine %s client %s SUSPENDED after repeated failures",
                routine_id, client_id,
            )
        return
        logger.error(
            "[RoutineExecutor] Execution %s timed out after %ds",
            exec_id, _ROUTINE_EXECUTION_TIMEOUT_S,
            extra={
                "execution_id": exec_id,
                "routine_id": routine_id,
                "client_id": client_id,
                "error_type": "timeout",
            },
        )
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {
                "status": "failed",
                "result_text": f"Erro: timeout após {_ROUTINE_EXECUTION_TIMEOUT_S}s",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        # P1: circuit breaker — conta falha
        new_status = await asyncio.to_thread(
            _record_routine_failure_sync, client_id, routine_id
        )
        if new_status == "suspended":
            logger.warning(
                "[CircuitBreaker] routine %s client %s SUSPENDED after repeated failures",
                routine_id, client_id,
            )

    except Exception as exc:
        logger.exception("[RoutineExecutor] Execution %s failed", exec_id)
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {
                "status": "failed",
                "result_text": f"Erro: {exc}",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        # P1: circuit breaker — conta falha
        new_status = await asyncio.to_thread(
            _record_routine_failure_sync, client_id, routine_id
        )
        if new_status == "suspended":
            logger.warning(
                "[CircuitBreaker] routine %s client %s SUSPENDED after repeated failures",
                routine_id, client_id,
                )


async def run_dispatched_executions(
    claimed: list[dict], context_service: ContextService
) -> None:
    """P2: executa todas as rotinas do batch em paralelo (gather), respeitando
    o semáforo por cliente (max 4). Execuções de clientes diferentes rodam
    simultaneamente; execuções do mesmo cliente são limitadas pelo semáforo."""
    if not claimed:
        return

    await asyncio.gather(
        *[_run_single_execution(execution, context_service) for execution in claimed],
        return_exceptions=True,
    )


# ---------------------------------------------------------------------------
# Core execution engine
# ---------------------------------------------------------------------------


async def _execute_one(
    execution: dict, context_service: ContextService
) -> tuple[str, str]:
    exec_id = str(execution["id"])
    client_id = UUID(str(execution["client_id"]))
    routine_id = str(execution["routine_id"])

    has_pending = await asyncio.to_thread(_has_pending_approvals_sync, exec_id)
    if has_pending:
        raise RuntimeError(f"Execution {exec_id} blocked by pending approval_requests")

    row = await asyncio.to_thread(_fetch_routine_sync, routine_id)
    if not row:
        raise RuntimeError(f"Routine '{routine_id}' not found")

    routine_name: str = row.get("name") or routine_id
    steps: list[dict] = row.get("steps") or []

    client_ctx = await context_service.get_client_context_by_id(client_id)
    nome_empresa = client_ctx.nome_empresa if client_ctx else "Blu"
    tier: str = (client_ctx.tier if client_ctx else None) or "BASIC"
    trigger_data: dict = execution.get("trigger_data") or {}

    # Fetch website_url from company_profile JSONB so {{website_url}} templates resolve.
    _clientes_row = await asyncio.to_thread(
        lambda: get_supabase_client(use_service_role=True)
        .table("clientes_blu")
        .select("company_profile")
        .eq("client_id", str(client_id))
        .maybe_single()
        .execute()
    )
    _company_profile: dict = (_clientes_row.data or {}).get("company_profile") or {}
    website_url: str = _company_profile.get("website_url") or _company_profile.get("website") or ""

    # Load per-client config overrides (days_inactive, lookback_months, etc.)
    client_config_row = await asyncio.to_thread(
        _fetch_client_routine_config_sync, str(client_id), routine_id
    )
    client_config: dict[str, object] = {}
    if client_config_row and client_config_row.get("config"):
        for k, v in client_config_row["config"].items():
            # Coerce numeric strings from select fields to proper types
            try:
                client_config[k] = int(v)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                try:
                    client_config[k] = float(v)  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    client_config[k] = v

    # Seed defaults from config_schema so {{key}} templates resolve even when
    # the client has no per-routine config override for that field.
    # client_config values win over schema defaults (applied after).
    schema_defaults: dict[str, object] = {}
    for field in (row.get("config_schema") or []):
        key = field.get("key")
        default = field.get("default")
        if key and default is not None:
            schema_defaults[key] = default

    # HITL resume: load saved progress when returning from awaiting_approval
    saved_metadata: dict = dict(execution.get("result_metadata") or {})
    resume_from: int = int(saved_metadata.pop("_resume_from_step", 0) or 0)

    # Initialise shared state — trigger data + execution metadata + client config.
    # `tier` is assigned after **client_config so a free-form config field named
    # "tier" cannot silently overwrite the value resolved from the DB.
    state: dict[str, Any] = {
        **trigger_data,
        "client_id": str(client_id),
        "routine_name": routine_name,
        "exec_id": exec_id,
        "nome_empresa": nome_empresa,
        "website_url": website_url,  # resolves {{website_url}} in crawl steps
        **schema_defaults,   # config_schema defaults — lowest priority
        **client_config,     # per-client overrides — wins over schema defaults
        "tier": tier,        # must come last — never overridden by client_config
    }

    # Merge saved state from a previous (paused) execution run
    if resume_from:
        state.update({k: v for k, v in saved_metadata.items() if k != "exec_id"})
        logger.info("[RoutineExecutor] %s → resuming HITL at step %d", exec_id, resume_from)

    result_parts: list[str] = []
    last_worker_slug = ""

    # -------------------------------------------------------------------------
    # Group steps by parallel_group — steps in the same group run concurrently,
    # steps without a group (or with different group names) run sequentially.
    # Example step: {"id": "get_cash", "type": "function", "parallel_group": "fetch", ...}
    # -------------------------------------------------------------------------
    from itertools import groupby as _groupby

    def _group_key(s: dict) -> tuple:
        """Steps with the same non-null parallel_group are batched together."""
        pg = s.get("parallel_group")
        if pg:
            return ("parallel", pg)
        # Sequential steps use a unique key so they form singleton groups
        return ("sequential", s.get("id") or s.get("step", 0))

    # Build ordered list of (is_parallel, [steps]) batches preserving original order
    step_batches: list[tuple[bool, list[dict]]] = []
    for key, group in _groupby(steps, key=_group_key):
        batch = list(group)
        step_batches.append((key[0] == "parallel", batch))

    async def _run_step(step: dict) -> tuple[str, dict, str]:
        """Execute a single step and return (step_id, outputs, worker_slug)."""
        step_n   = step.get("step", 0)
        step_id  = step.get("id") or f"step_{step_n}"
        step_type: str | None = step.get("type")

        # Skip already-completed steps when resuming after HITL approval
        if resume_from and step_n < resume_from:
            logger.info("[RoutineExecutor] %s → step '%s' skipped (HITL resume)", exec_id, step_id)
            return step_id, {}, ""

        logger.info("[RoutineExecutor] %s → step '%s' (type=%s)", exec_id, step_id, step_type or "legacy")

        resolved_inputs = _resolve_templates(step.get("inputs", {}), state)
        slug = ""

        if step_type is None:
            logger.warning(
                "[RoutineExecutor] Step '%s' has no type — skipping (legacy format not supported)",
                step_id,
            )
            return step_id, {}, ""

        elif step_type == "function":
            config_override = {k: client_config[k] for k in resolved_inputs if k in client_config}
            if config_override:
                resolved_inputs = {**resolved_inputs, **config_override}
            outputs = await _execute_function_step(step, resolved_inputs, str(client_id))

        elif step_type == "skill":
            outputs, slug = await _execute_skill_step(
                step, resolved_inputs, state, nome_empresa, context_service
            )

        elif step_type == "llm":
            outputs = await _execute_llm_step(step, state, nome_empresa)

        elif step_type == "artifact":
            fn_name = step.get("function") or _ARTIFACT_TYPE_DEFAULT_FN.get(step.get("artifact_type", ""), "")
            if fn_name == "channels.create_alert":
                resolved_inputs = {
                    **resolved_inputs,
                    "execution_id": exec_id,
                    "routine_id": str(routine_id),
                }
            # ── D2 dedupe: side-effectful artifacts get a claim row before delivery.
            # Inferimos pelo fn_name (robusto a steps sem artifact_type populado).
            _SIDE_EFFECTFUL_FNS = {
                "channels.send_email": "email",
                "channels.send_email_batch": "email",
                "channels.send_whatsapp": "whatsapp",
                "storage.save_context_document": "document",
            }
            artifact_type = step.get("artifact_type") or _SIDE_EFFECTFUL_FNS.get(fn_name, "")
            claim_id: str | None = None
            if fn_name in _SIDE_EFFECTFUL_FNS:
                from agent_api.core.artifact_dedupe import claim_artifact, mark_artifact_sent, mark_artifact_failed
                claim_id = await claim_artifact(
                    execution_id=exec_id,
                    step_id=step_id,
                    client_id=str(client_id),
                    artifact_type=artifact_type or _SIDE_EFFECTFUL_FNS[fn_name],
                    function_name=fn_name,
                )
                if claim_id is None:
                    logger.warning(
                        "[RoutineExecutor] %s → step '%s' (%s) SKIPPED: already delivered (dedupe)",
                        exec_id, step_id, fn_name,
                    )
                    return step_id, {"deduped": True}, ""
            try:
                outputs = await _execute_artifact_step(step, resolved_inputs, str(client_id))
                if claim_id:
                    await mark_artifact_sent(claim_id, outputs)
            except Exception:
                if claim_id:
                    import traceback
                    await mark_artifact_failed(claim_id, traceback.format_exc(limit=3))
                raise

        elif step_type == "approval":
            resolved_inputs = {**resolved_inputs, "execution_id": exec_id}
            outputs = await _execute_artifact_step(
                {**step, "function": "channels.request_approval"},
                resolved_inputs,
                str(client_id),
            )

        else:
            logger.warning(
                "[RoutineExecutor] Unknown step type '%s' at '%s' — skipping",
                step_type, step_id,
            )
            return step_id, {}, ""

        return step_id, outputs, slug

    for is_parallel, batch in step_batches:
        if is_parallel:
            # Run all steps in the batch concurrently
            logger.info(
                "[RoutineExecutor] %s → parallel group '%s' (%d steps)",
                exec_id, batch[0].get("parallel_group"), len(batch),
            )
            results = await asyncio.gather(
                *[_run_step(s) for s in batch],
                return_exceptions=True,
            )
            for step, result in zip(batch, results):
                step_id  = step.get("id") or f"step_{step.get('step', 0)}"
                on_failure = step.get("on_failure", "continue")
                if isinstance(result, Exception):
                    logger.error(
                        "[RoutineExecutor] Parallel step '%s' of %s failed: %s: %s",
                        step_id, exec_id, type(result).__name__, result,
                        exc_info=result,
                    )
                    if on_failure == "halt":
                        raise result
                    result_parts.append(f"{step_id}: falhou ({result}), continuando")
                    continue
                step_id_out, step_outputs, slug = result
                if slug:
                    last_worker_slug = slug
                for k, v in step_outputs.items():
                    state[k] = "" if (v is None or v == [] or v == {}) else v
                summary_val = step_outputs.get("summary") or _first_scalar(step_outputs) or "ok"
                result_parts.append(f"{step_id_out}: {str(summary_val)[:300]}")
        else:
            # Single sequential step
            step = batch[0]
            step_id  = step.get("id") or f"step_{step.get('step', 0)}"
            on_failure = step.get("on_failure", "continue")
            try:
                step_id_out, step_outputs, slug = await _run_step(step)
            except Exception as exc:
                logger.exception("[RoutineExecutor] Step '%s' of %s failed", step_id, exec_id)
                if on_failure == "halt":
                    raise
                result_parts.append(f"{step_id}: falhou ({exc}), continuando")
                continue

            if slug:
                last_worker_slug = slug

            # HITL approval gate
            if step_outputs.get("_awaiting_approval"):
                state["_resume_from_step"] = step.get("step", 0) + 1
                state.update(step_outputs)
                await asyncio.to_thread(
                    _update_execution_sync, exec_id,
                    {"result_metadata": _serialisable(state)},
                )
                # Checkpoint em shared_business_memory (secundário — Issue #21)
                await _checkpoint_to_shared_memory(
                    client_id=str(client_id),
                    routine_id=state["routine_name"],
                    exec_id=exec_id,
                    step_number=step.get("step", 0),
                    state=state,
                )
                result_parts.append(f"{step_id_out}: aguardando aprovação humana")
                return (
                    "\n".join(result_parts) + "\n" + _AWAITING_APPROVAL_MARKER,
                    last_worker_slug,
                )

            for k, v in step_outputs.items():
                state[k] = "" if (v is None or v == [] or v == {}) else v

            summary_val = step_outputs.get("summary") or _first_scalar(step_outputs) or "ok"
            result_parts.append(f"{step_id_out}: {str(summary_val)[:300]}")

        # Checkpoint after each batch (parallel or sequential)
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {"result_metadata": _serialisable(state)},
        )

        # Checkpoint em shared_business_memory (secundário — Issue #21)
        if is_parallel:
            last_step = max((s.get("step", 0) for s in batch), default=0)
        else:
            last_step = batch[0].get("step", 0)
        await _checkpoint_to_shared_memory(
            client_id=str(client_id),
            routine_id=state["routine_name"],
            exec_id=exec_id,
            step_number=last_step,
            state=state,
        )
        if last_step == 1:
            logger.info(
                "Routine checkpoint enabled: routine=%s exec=%s client=%s",
                state["routine_name"], exec_id, str(client_id),
            )


    await _fire_on_complete_events(str(client_id), steps)

    return "\n".join(result_parts) or "Concluído.", last_worker_slug


# ---------------------------------------------------------------------------
# Shared memory checkpoint (Issue #21)
# ---------------------------------------------------------------------------


async def _checkpoint_to_shared_memory(
    client_id: str,
    routine_id: str,
    exec_id: str,
    step_number: int,
    state: dict,
) -> None:
    """
    Salva checkpoint do estado de execução em shared_business_memory.

    Design decisions (Issue #21):
    - entity_type='routine' (DD-01)
    - Key pattern: checkpoint:run:{exec_id}:step:{N} + current_state:{routine_id} (DD-04)
    - Falha NÃO interrompe o step — result_metadata é o checkpoint primário (DD-03)

    Args:
        client_id: UUID do cliente
        routine_id: Slug da rotina (ex: 'daily_insights')
        exec_id: UUID da execução corrente
        step_number: Número ordinal do step que acabou de executar
        state: State dict completo (pós-step)
    """
    try:
        client = get_supabase_client()
        client.rpc(
            "upsert_routine_checkpoint",
            {
                "p_client_id": client_id,
                "p_routine_id": routine_id,
                "p_exec_id": exec_id,
                "p_step_number": step_number,
                "p_state_value": _serialisable(state),
            },
        ).execute()
    except Exception as e:
        logger.warning(
            "shared_business_memory checkpoint failed (non-fatal): "
            "routine=%s exec=%s step=%s: %s",
            routine_id, exec_id, step_number, e,
        )


# ---------------------------------------------------------------------------
# on_complete event hooks
# ---------------------------------------------------------------------------


async def _fire_on_complete_events(client_id: str, steps: list[dict]) -> None:
    """
    After all steps complete, check each step for on_complete.fire_event.
    If set, calls fire_event_for_client via Supabase RPC so event-triggered
    routines (e.g. daily_briefing after morning_ready) enqueue automatically.
    """
    db = get_supabase_client(use_service_role=True)
    for step in steps:
        on_complete: dict | None = step.get("on_complete")
        if not on_complete:
            continue
        event_type: str = on_complete.get("fire_event", "")
        if not event_type:
            continue
        payload: dict = on_complete.get("payload", {})
        try:
            await asyncio.to_thread(
                lambda et=event_type, p=payload: db.rpc(
                    "fire_event_for_client",
                    {"p_event_type": et, "p_client_id": client_id, "p_trigger_data": p},
                ).execute()
            )
            logger.info(
                "[RoutineExecutor] on_complete fired event='%s' for client=%s",
                event_type, client_id,
            )
        except Exception as exc:
            logger.warning(
                "[RoutineExecutor] on_complete fire_event='%s' failed for client=%s: %s",
                event_type, client_id, exc,
            )


# ---------------------------------------------------------------------------
# Step executors
# ---------------------------------------------------------------------------


async def _execute_function_step(
    step: dict, resolved_inputs: dict, client_id: str
) -> dict:
    from agent_api.core.routine_functions import call as call_function
    fn_name: str = step.get("function", "")
    if not fn_name:
        raise ValueError(f"function step missing 'function' key: {step}")
    return await call_function(fn_name, resolved_inputs, client_id)


async def _execute_llm_step(
    step: dict,
    state: dict[str, Any],
    nome_empresa: str,
) -> dict:
    """
    Direct LLM call using a Langfuse chat prompt (blu/* naming convention).

    Fetches the chat prompt by name, compiles variables from the current routine
    state, invokes the model, and optionally extracts structured JSON output.

    Step fields:
        prompt_name — Langfuse chat prompt key (e.g. "blu/meeting_brief_v1")
        outputs     — schema dict used to extract structured output from LLM text
        model_tier  — optional; "fast" | "default" | "powerful" (default: "default")
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from blu_llm_service import ModelTier, get_model

    prompt_name: str = step.get("prompt_name", "")
    outputs_schema = step.get("outputs", {})

    if not prompt_name:
        raise ValueError(f"llm step missing 'prompt_name': {step}")

    # Build a flat string-safe context for template interpolation
    ctx: dict[str, str] = {"nome_empresa": nome_empresa}
    for k, v in state.items():
        if isinstance(v, (dict, list)):
            ctx[k] = json.dumps(v, ensure_ascii=False)
        elif v is None:
            ctx[k] = ""
        else:
            ctx[k] = str(v)

    # Fetch and compile the Langfuse prompt (handles both text and chat types)
    try:
        from langfuse import Langfuse
        lf_client = Langfuse()
        prompt_obj = await asyncio.to_thread(lf_client.get_prompt, prompt_name)
        compiled = prompt_obj.compile(**ctx)
    except Exception as exc:
        logger.warning("[RoutineExecutor] llm step: failed to load prompt '%s': %s", prompt_name, exc)
        raise

    # compiled is str for text prompts, list[dict] for chat prompts
    if isinstance(compiled, str):
        lc_messages = [
            SystemMessage(content=compiled),
            HumanMessage(content="Gere o output conforme as instruções acima."),
        ]
    else:
        lc_messages = []
        for msg in compiled:
            role = (msg.get("role") or "user").lower()
            content = msg.get("content", "")
            lc_messages.append(SystemMessage(content=content) if role == "system" else HumanMessage(content=content))

    if not lc_messages:
        raise ValueError(f"llm step: prompt '{prompt_name}' compiled to empty messages")

    model_tier_val = step.get("model_tier", ModelTier.DEFAULT.value)
    try:
        model_tier = ModelTier(model_tier_val)
    except ValueError:
        logger.warning("[RoutineExecutor] Unknown model_tier '%s' in llm step, using DEFAULT", model_tier_val)
        model_tier = ModelTier.DEFAULT
    llm = get_model(tier=model_tier)
    response = await llm.ainvoke(lc_messages)
    result_text = response.content if hasattr(response, "content") else str(response)

    step_outputs: dict[str, Any] = {"summary": result_text[:500]}

    if outputs_schema:
        extracted = _extract_json_from_text(result_text, outputs_schema)
        if extracted:
            step_outputs.update(extracted)
        else:
            logger.warning("[RoutineExecutor] llm step '%s' returned no structured output", prompt_name)

    logger.info("[RoutineExecutor] llm step '%s' completed (%d chars)", prompt_name, len(result_text))
    return step_outputs


async def _execute_skill_step(
    step: dict,
    resolved_inputs: dict,
    state: dict[str, Any],
    nome_empresa: str,
    context_service: Any,
) -> tuple[dict, str]:
    skill_slug: str = step.get("skill_slug") or step.get("agent", "")
    task_template: str = step.get("task_template") or step.get("action", "")
    outputs_schema = step.get("outputs", {})

    if not skill_slug:
        raise ValueError(f"skill step missing 'skill_slug': {step}")

    merged = {**state, **resolved_inputs}
    task = _resolve_templates(task_template, merged)
    tier: str = state.get("tier", "BASIC")

    # Pipeline routines expect Jinja-style placeholders like `{{...}}`; normalize
    # the resolved task into a plain f-string/template form when needed.
    task = task.replace("{{", "${").replace("}}", "}")

    # Phase 4: if this step has an outputs schema, append a structured-output
    # instruction so the LLM returns a JSON block that _extract_json_from_text
    # can reliably capture — even when output_tool_schema is not wired through
    # to the graph level yet.
    if outputs_schema:
        import json as _json
        keys_desc = ", ".join(f'"{k}"' for k in outputs_schema)
        task = (
            task.rstrip()
            + f"\n\nResponda EXCLUSIVAMENTE com um objeto JSON com a(s) chave(s): {keys_desc}. "
            + "Sem texto fora do JSON. Exemplo: "
            + _json.dumps({k: "..." for k in outputs_schema})
        )

    result = await _run_skill_direct(
        skill_slug, task, nome_empresa, context_service,
        tier=tier,
        output_tool_schema=outputs_schema or None,
        execution_id=state.get("exec_id"),
        routine_id=state.get("routine_name"),
        client_id_str=state.get("client_id"),
    )

    step_outputs: dict[str, Any] = {
        "summary": (result.summary or "")[:500],
        "worker_slug": skill_slug,
    }

    # Phase 4: structured_data comes from tool_use; fall back to text extraction
    if outputs_schema:
        if result.structured_data:
            step_outputs.update(result.structured_data)
        elif result.summary:
            extracted = _extract_json_from_text(result.summary, outputs_schema)
            if extracted:
                step_outputs.update(extracted)
            elif len(outputs_schema) == 1:
                key = next(iter(outputs_schema))
                candidate = result.summary.strip()
                try:
                    parsed = json.loads(candidate)
                except (json.JSONDecodeError, TypeError):
                    parsed = None

                value = ""
                if isinstance(parsed, dict):
                    value = parsed.get(key) or candidate
                elif isinstance(parsed, list):
                    value = json.dumps(parsed, ensure_ascii=False)
                else:
                    value = candidate
                step_outputs[key] = value
            else:
                logger.warning(
                    "[RoutineExecutor] skill '%s' returned no structured output",
                    skill_slug,
                )

        _json2 = json

        for k in outputs_schema:
            if k in step_outputs and not isinstance(step_outputs[k], str):
                step_outputs[k] = _json2.dumps(step_outputs[k], ensure_ascii=False)

    if result.error:
        logger.warning("[RoutineExecutor] skill '%s' error: %s", skill_slug, result.error)

    return step_outputs, skill_slug


_ARTIFACT_TYPE_DEFAULT_FN: dict[str, str] = {
    "email": "channels.send_email_batch",
    "alert": "channels.create_alert",
    "document": "storage.save_context_document",
    "whatsapp": "channels.send_whatsapp",
}


async def _execute_artifact_step(
    step: dict, resolved_inputs: dict, client_id: str
) -> dict:
    from agent_api.core.routine_artifacts import call as call_artifact
    fn_name: str = step.get("function", "")
    if not fn_name:
        artifact_type: str = step.get("artifact_type", "")
        fn_name = _ARTIFACT_TYPE_DEFAULT_FN.get(artifact_type, "")
    if not fn_name:
        raise ValueError(
            f"artifact step missing 'function' key or unknown 'artifact_type': {step}"
        )
    return await call_artifact(fn_name, resolved_inputs, client_id)




# ---------------------------------------------------------------------------
# Direct skill execution (routine path — bypasses specialist graph)
# ---------------------------------------------------------------------------


async def _run_skill_direct(
    skill_name: str,
    task: str,
    nome_empresa: str,
    context_service: Any,
    tier: str = "BASIC",
    output_tool_schema: dict | list | None = None,
    execution_id: str | None = None,
    routine_id: str | None = None,
    client_id_str: str | None = None,
):
    """
    Execute a skill directly via SkillFactory, bypassing the full specialist
    graph and classify_skill_intent_node.  Used by routine steps where
    skill_slug points to a SKILL_REGISTRY key, not an agent slug.

    Falls back to _invoke_worker (agent path) when the skill name is not in
    SKILL_REGISTRY — ensures backward compatibility during migration.
    """
    from blu_agent_framework.skill_factory import SkillFactory
    from blu_agent_framework.skills import SKILL_REGISTRY
    from blu_agent_framework.supervisor import WorkerResult
    from blu_llm_service import ModelTier, get_model
    from blu_tool_registry.resource_resolver import ResourceResolver
    from langchain_core.messages import HumanMessage as _HumanMessage

    from agent_api.core.factory import get_mcp_executor

    logger.info(
        "[DEBUG _run_skill_direct] skill_name='%s' keys=%d has_key=%s",
        skill_name,
        len(SKILL_REGISTRY),
        skill_name in SKILL_REGISTRY,
    )
    if skill_name not in SKILL_REGISTRY:
        # Fallback: treat as agent slug (legacy / migration period)
        logger.warning(
            "[_run_skill_direct] '%s' not in SKILL_REGISTRY — falling back to _invoke_worker",
            skill_name,
        )
        return await _invoke_worker(
            skill_name, task, nome_empresa, context_service,
            tier=tier,
            output_tool_schema=output_tool_schema,
            execution_id=execution_id,
            routine_id=routine_id,
            client_id_str=client_id_str,
        )

    skill = SKILL_REGISTRY[skill_name]

    # Resolve tools allowed for this skill at the client's tier
    allowed_tools: list[str] = ResourceResolver.filter_tools(
        list(skill.required_tool_names or []), skill_name, tier
    )

    llm = get_model(tier=ModelTier.DEFAULT)  # skills use DEFAULT tier model
    mcp_executor = get_mcp_executor()

    skill_factory = SkillFactory(
        llm=llm,
        mcp_executor=mcp_executor,
        agent_enabled_tools=allowed_tools,
    )

    # Build a minimal parent_state so SkillFactory.run() has the context it needs
    parent_state: dict = {
        "session_id": f"routine-skill-{skill_name}",
        "client_id": client_id_str or "",
        "thread_id": "",
        "channel": "api",
        "agent_name": skill_name,
        "agent_role": skill_name,
        "tier": tier,
        "nome_empresa": nome_empresa,
        "current_domain": None,
        "client_context": {"nome_empresa": nome_empresa, "tier": tier},
        "metadata": {},
        "intent_tags": list(skill.tags),
        "loaded_context_keys": [],
        "messages": [_HumanMessage(content=task)],
        "system_prompt": "",
        "turn_count": 0,
        "max_turns": skill.max_turns,
        "tool_results": [],
        "pending_tool_calls": [],
        "tool_to_execute": None,
        "tool_args": None,
        "last_tool_result": None,
        "ended": False,
        "error": None,
        "structured_data": None,
    }

    try:
        skill_result = await skill_factory.run(skill_name, parent_state)  # type: ignore[arg-type]
    except Exception as exc:
        logger.exception("[_run_skill_direct] Skill '%s' raised: %s", skill_name, exc)
        return WorkerResult(summary="", worker_slug=skill_name, error=str(exc))

    if not skill_result.success:
        logger.warning(
            "[_run_skill_direct] Skill '%s' failed: %s", skill_name, skill_result.error
        )

    # Normalize SkillResult → WorkerResult so _execute_skill_step stays unchanged
    # SkillResult.output is the full LangGraph state dict (messages, session_id, etc.)
    # — it never carries "text"/"summary" keys directly. The correct way to extract
    # the narrative is last_text(), which walks messages looking for the last AIMessage.
    output_text = skill_result.last_text()
    structured: dict | None = None
    if not output_text and skill_result.output:
        if isinstance(skill_result.output, dict):
            # fallback: look for explicit text/summary keys (future-proof)
            output_text = skill_result.output.get("text") or skill_result.output.get("summary") or ""
            structured = {k: v for k, v in skill_result.output.items() if k not in ("text", "summary")} or None
        else:
            output_text = str(skill_result.output)

    return WorkerResult(
        summary=output_text,
        worker_slug=skill_name,
        structured_data=structured,
        error=skill_result.error,
    )


# ---------------------------------------------------------------------------
# Worker invocation
# ---------------------------------------------------------------------------


async def _invoke_worker(
    slug: str,
    task: str,
    nome_empresa: str,
    context_service: Any,
    tier: str = "BASIC",
    output_tool_schema: dict | list | None = None,
    execution_id: str | None = None,   # P2-A: para Langfuse trace de rotinas
    routine_id: str | None = None,     # P2-A: tag no trace
    client_id_str: str | None = None,  # P2-A: tag no trace
):
    from blu_agent_framework.builder import AgentBuilder
    from blu_agent_framework.config import AgentConfig
    from blu_agent_framework.registry import AgentTypeRegistry
    from blu_agent_framework.skill_factory import SkillFactory
    from blu_agent_framework.state import create_initial_state
    from blu_agent_framework.supervisor import WorkerResult
    from blu_llm_service import ModelTier, get_model
    from blu_tool_registry.resource_resolver import ResourceResolver
    from blu_tool_registry.tier_validator import TierValidator
    from langchain_core.messages import AIMessage as _AIMessage
    from langchain_core.messages import HumanMessage as _HumanMessage

    from agent_api.core.factory import get_mcp_executor

    cfg = AgentTypeRegistry.get(slug)
    if not cfg:
        return WorkerResult(
            summary="",
            worker_slug=slug,
            error=f"Unknown worker: {slug}",
        )

    # Issue 5: enforce tier_required via ResourceResolver (FeatureRegistry) as primary.
    # Falls back to TierValidator legacy check for agents outside the feature map.
    if not ResourceResolver.can_access_agent(slug, tier) and not TierValidator.is_tier_higher_or_equal(tier, cfg.tier_required.value):
        return WorkerResult(
            summary="",
            worker_slug=slug,
            error=(
                f"Client tier {tier!r} cannot invoke worker {slug!r} "
                f"(requires {cfg.tier_required.value!r})"
            ),
        )

    # Issue 3: filter the worker's tool list to tools accessible at this tier.
    # Primary: FeatureRegistry. Fallback: per-tool ToolRegistry check.
    allowed_tools: list[str] = ResourceResolver.filter_tools(list(cfg.enabled_tools), slug, tier)

    llm = get_model(tier=cfg.model_tier)
    mcp_executor = get_mcp_executor()

    agent_cfg = AgentConfig(
        name=cfg.name,
        role=cfg.slug,
        enabled_tools=allowed_tools,
        max_turns=cfg.max_turns,
    )
    skill_factory = SkillFactory(
        llm=llm,
        mcp_executor=mcp_executor,
        agent_enabled_tools=allowed_tools,
    )
    graph = (
        AgentBuilder(agent_cfg, mcp_executor=mcp_executor, checkpointer=None)
        .with_llm(llm)
        .with_context_service(context_service)
        .with_skill_factory(skill_factory)
        .use_specialist_graph(cfg)
        .build()
    )

    initial_state = create_initial_state(
        session_id=f"routine-{slug}",
        client_id="",
        messages=[_HumanMessage(content=task)],
        agent_name=cfg.name,
        agent_role=cfg.slug,
        max_turns=cfg.max_turns,
        client_context={"nome_empresa": nome_empresa, "tier": tier},
    )

    # P2-A: Langfuse trace para execuções de rotina
    # Usa get_langfuse_config com session_id = execution_id para correlacionar
    # a trace do agente com a linha em client_routine_executions
    invoke_config: dict = {"recursion_limit": 30}
    if execution_id:
        try:
            from agent_api.core.observability import get_langfuse_config
            lf_cfg = get_langfuse_config(
                session_id=execution_id,
                client_id=client_id_str or "",
                tags=["routine", slug, routine_id or "unknown"],
                trace_name=f"routine:{routine_id or slug}:{execution_id[:8] if execution_id else ''}",
            )
            # merge: configurable já vem do get_langfuse_config, recursion_limit é separado
            invoke_config = {**lf_cfg, "recursion_limit": 30}
        except Exception as _lf_exc:
            logger.debug("[_invoke_worker] Langfuse config failed for routine: %s", _lf_exc)

    try:
        # P0: recursion_limit impede loop infinito de tool calls no LangGraph
        result_state = await graph.ainvoke(initial_state, invoke_config)
    except Exception as exc:
        logger.exception("[_invoke_worker] Specialist '%s' raised: %s", slug, exc)
        return WorkerResult(summary="", worker_slug=slug, error=str(exc))

    final_messages = result_state.get("messages", [])
    last_ai = next(
        (m for m in reversed(final_messages) if isinstance(m, _AIMessage) and m.content),
        None,
    )
    summary = str(last_ai.content) if last_ai else ""

    return WorkerResult(
        summary=summary,
        worker_slug=slug,
        structured_data=result_state.get("structured_data"),
    )


# ---------------------------------------------------------------------------
# Post-execution notification
# ---------------------------------------------------------------------------


async def _notify_client(execution: dict, result_text: str) -> None:
    client_id = str(execution["client_id"])
    routine_id = str(execution["routine_id"])

    row = await asyncio.to_thread(
        _fetch_client_routine_config_sync, client_id, routine_id
    )
    if not row:
        return

    channel: str = row.get("notify_channel") or "app"
    config: dict = row.get("config") or {}
    routine_name: str = row.get("name") or routine_id
    first_line = (result_text.split("\n")[0])[:300] if result_text else ""
    message_body = f"Blu: {routine_name} concluída.\n{first_line}\nVeja em app.blu.com.br"

    if channel == "whatsapp":
        phone: str | None = config.get("phone_e164")
        if phone:
            try:
                from blu_twilio_client import TwilioClient
                from blu_twilio_client.config import get_twilio_settings
                twilio = TwilioClient(get_twilio_settings())
                await asyncio.to_thread(twilio.send_whatsapp, phone, message_body)
                logger.info("[RoutineExecutor] WhatsApp sent to %s for %s", phone, routine_name)
            except Exception as exc:
                logger.warning("[RoutineExecutor] WhatsApp notify failed for %s: %s", client_id, exc)

    elif channel == "email":
        email: str | None = config.get("email")
        if email:
            try:
                from agent_api.core.routine_artifacts import _deliver_email  # noqa: PLC2701
                await _deliver_email(email, f"Blu: {routine_name} concluída", message_body, client_id)
                logger.info("[RoutineExecutor] Email notify sent for %s", routine_name)
            except Exception as exc:
                logger.warning("[RoutineExecutor] Email notify failed for %s: %s", client_id, exc)

    logger.info(
        "[RoutineExecutor] Completed: client=%s routine=%s channel=%s",
        client_id, routine_id, channel,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_scalar(d: dict) -> str | None:
    """Return the first scalar value in a dict as a string, for summary lines."""
    for v in d.values():
        if isinstance(v, (str, int, float, bool)):
            return str(v)
    return None
