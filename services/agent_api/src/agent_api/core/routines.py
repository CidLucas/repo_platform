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
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from blu_supabase_client import get_supabase_client

if TYPE_CHECKING:
    from blu_context_service import ContextService

logger = logging.getLogger(__name__)

_mcp_semaphore = asyncio.Semaphore(1)


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
    table = "client_routines" if _is_custom_routine(routine_id) else "cross_agent_routines"
    return (
        db.table(table)
        .select("name, steps")
        .eq("id", routine_id)
        .maybe_single()
        .execute()
        .data
    )


def _fetch_client_routine_config_sync(client_id: str, routine_id: str) -> dict | None:
    return (
        get_supabase_client()
        .table("client_routines")
        .select("notify_channel, config, name")
        .eq("client_id", client_id)
        .eq("routine_id", routine_id)
        .maybe_single()
        .execute()
        .data
    )


def _update_execution_sync(execution_id: str, payload: dict) -> None:
    get_supabase_client().table("client_routine_executions").update(payload).eq(
        "id", execution_id
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


def _fetch_triggered_routines_sync(trigger_type: str) -> list[dict]:
    """Fetch catalog routines with a given trigger_type (cron | numeric | event)."""
    try:
        return (
            get_supabase_client()
            .table("cross_agent_routines")
            .select("id, name, trigger_config")
            .eq("trigger_type", trigger_type)
            .execute()
            .data or []
        )
    except Exception as exc:
        logger.warning("[TriggerPoller] failed to fetch '%s' routines: %s", trigger_type, exc)
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

    routines = await asyncio.to_thread(_fetch_triggered_routines_sync, "cron")
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
    Supported metrics: new_clients_monthly_rate.
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
        window_months: int = int(cfg.get("window_months", 12))

        if metric != "new_clients_monthly_rate":
            logger.debug("[TriggerPoller] unsupported metric '%s' — skipping", metric)
            continue

        cooldown_hours: int = int(cfg.get("cooldown_hours", 24))

        client_rows = await asyncio.to_thread(_fetch_active_client_routines_sync, routine_id)
        now_num = datetime.now(timezone.utc)
        for cr in client_rows:
            client_id = str(cr["client_id"])

            # Per-client config overrides for threshold and window_months
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
                current, avg = await asyncio.to_thread(
                    _get_new_clients_rate_sync, client_id, effective_window
                )
                if avg == 0 or current >= effective_threshold * avg:
                    continue  # condition not met or no data

                exec_id = await asyncio.to_thread(
                    _dispatch_execution_sync,
                    client_id,
                    routine_id,
                    "numeric",
                    {"metric": metric, "current_value": current, "avg_value": avg, "threshold": effective_threshold},
                )
                if exec_id:
                    logger.info(
                        "[TriggerPoller] numeric: routine=%s client=%s current=%.1f avg=%.1f exec=%s",
                        routine_id, client_id, current, avg, exec_id,
                    )
                    count += 1
            except Exception as exc:
                logger.warning("[TriggerPoller] numeric eval failed for client %s: %s", client_id, exc)

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


async def run_dispatched_executions(
    claimed: list[dict], context_service: ContextService
) -> None:
    if not claimed:
        return

    for execution in claimed:
        exec_id = str(execution["id"])
        try:
            async with _mcp_semaphore:
                from agent_api.core.factory import get_mcp_manager
                get_mcp_manager().set_client_id(str(execution["client_id"]))
                result_text, worker_slug = await _execute_one(execution, context_service)

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
            await _notify_client(execution, result_text)

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
    trigger_data: dict = execution.get("trigger_data") or {}

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

    # Initialise shared state — trigger data + execution metadata + client config
    state: dict[str, Any] = {
        **trigger_data,
        "client_id": str(client_id),
        "routine_name": routine_name,
        "exec_id": exec_id,
        "nome_empresa": nome_empresa,
        **client_config,  # config values available for template resolution
    }

    result_parts: list[str] = []
    last_worker_slug = ""

    for step in steps:
        step_n = step.get("step", 0)
        step_id = step.get("id") or f"step_{step_n}"
        step_type: str | None = step.get("type")
        on_failure: str = step.get("on_failure", "halt")

        logger.info("[RoutineExecutor] %s → step '%s' (type=%s)", exec_id, step_id, step_type or "legacy")

        try:
            if step_type is None:
                # ── Legacy step: {step, agent, action, output} ──────────────
                step_outputs, slug = await _execute_legacy_step(
                    step, state, nome_empresa, context_service
                )
                last_worker_slug = slug
            else:
                resolved_inputs = _resolve_templates(step.get("inputs", {}), state)

                if step_type == "function":
                    # Apply per-client config as override for any matching input keys
                    config_override = {k: client_config[k] for k in resolved_inputs if k in client_config}
                    if config_override:
                        resolved_inputs = {**resolved_inputs, **config_override}
                    step_outputs = await _execute_function_step(step, resolved_inputs, str(client_id))

                elif step_type == "skill":
                    step_outputs, slug = await _execute_skill_step(
                        step, resolved_inputs, state, nome_empresa, context_service
                    )
                    last_worker_slug = slug

                elif step_type == "artifact":
                    step_outputs = await _execute_artifact_step(step, resolved_inputs, str(client_id))

                else:
                    logger.warning(
                        "[RoutineExecutor] Unknown step type '%s' at '%s' — skipping",
                        step_type, step_id,
                    )
                    continue

        except Exception as exc:
            logger.exception("[RoutineExecutor] Step '%s' of %s failed", step_id, exec_id)
            if on_failure == "halt":
                raise
            # on_failure == "continue" — log and proceed
            result_parts.append(f"{step_id}: falhou ({exc}), continuando")
            continue

        # Merge step outputs into shared state
        state.update(step_outputs)

        # Checkpoint: persist current state so progress is visible/resumable
        await asyncio.to_thread(
            _update_execution_sync,
            exec_id,
            {"result_metadata": _serialisable(state)},
        )

        # Build summary line for the final result_text
        summary_val = (
            step_outputs.get("summary")
            or _first_scalar(step_outputs)
            or "ok"
        )
        result_parts.append(f"{step_id}: {str(summary_val)[:300]}")

    return "\n".join(result_parts) or "Concluído.", last_worker_slug


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

    # Phase 4: pass outputs schema so the worker is forced to call submit_step_output
    result = await _invoke_worker(
        skill_slug, task, nome_empresa, context_service,
        output_tool_schema=outputs_schema or None,
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
            else:
                logger.warning(
                    "[RoutineExecutor] skill '%s' returned no structured output",
                    skill_slug,
                )

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


async def _execute_legacy_step(
    step: dict,
    state: dict[str, Any],
    nome_empresa: str,
    context_service: Any,
) -> tuple[dict, str]:
    """
    Run a legacy-format step {step, agent, action, output}.
    Reproduces the original behaviour for backward compatibility.
    """
    action: str = step.get("action", "")
    agent_slug: str = step.get("agent", "")
    routine_name: str = state.get("routine_name", "")
    trigger_data = {
        k: v for k, v in state.items()
        if k not in ("client_id", "routine_name", "exec_id", "nome_empresa")
    }

    task = (
        f"[ROUTINE TASK]\nRoutine: {routine_name}\n"
        f"Action: {action}\n"
        f"Input: {json.dumps(trigger_data, ensure_ascii=False)}"
    )

    result = await _invoke_worker(agent_slug, task, nome_empresa, context_service)
    step_outputs = {"summary": (result.summary or "")[:500]}
    return step_outputs, agent_slug


# ---------------------------------------------------------------------------
# Worker invocation
# ---------------------------------------------------------------------------


async def _invoke_worker(
    slug: str,
    task: str,
    nome_empresa: str,
    context_service: Any,
    output_tool_schema: dict | list | None = None,
):
    from langchain_core.messages import AIMessage as _AIMessage
    from langchain_core.messages import HumanMessage as _HumanMessage
    from blu_agent_framework.builder import AgentBuilder
    from blu_agent_framework.config import AgentConfig
    from blu_agent_framework.registry import AgentTypeRegistry
    from blu_agent_framework.skill_factory import SkillFactory
    from blu_agent_framework.state import create_initial_state
    from blu_agent_framework.supervisor import WorkerResult
    from blu_llm_service import get_model
    from agent_api.core.factory import get_mcp_executor

    cfg = AgentTypeRegistry.get(slug)
    if not cfg:
        return WorkerResult(
            summary="",
            worker_slug=slug,
            error=f"Unknown worker: {slug}",
        )

    llm = get_model()
    mcp_executor = get_mcp_executor()

    agent_cfg = AgentConfig(
        name=cfg.name,
        role=cfg.slug,
        enabled_tools=cfg.enabled_tools,
        max_turns=cfg.max_turns,
    )
    skill_factory = SkillFactory(
        llm=llm,
        mcp_executor=mcp_executor,
        agent_enabled_tools=cfg.enabled_tools,
    )
    graph = (
        AgentBuilder(agent_cfg, mcp_executor=mcp_executor, checkpointer=None)
        .with_llm(llm)
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
        client_context={"nome_empresa": nome_empresa},
    )

    try:
        result_state = await graph.ainvoke(initial_state)
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
