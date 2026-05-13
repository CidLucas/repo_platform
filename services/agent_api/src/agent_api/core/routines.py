"""
Routine execution engine.

Picks up already-claimed routine executions, runs each step via a worker
invocation loop, stores the result, and notifies the client.

Concurrency guard: MCP manager's set_cliente_id() is stateful — the semaphore
ensures only one client's execution runs at a time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from blu_supabase_client import get_supabase_client

if TYPE_CHECKING:
    from blu_context_service import ContextService

logger = logging.getLogger(__name__)

_mcp_semaphore = asyncio.Semaphore(1)
_worker_invoker = None  # lazily initialized singleton


def _get_worker_invoker():
    global _worker_invoker
    if _worker_invoker is None:
        from blu_agent_framework.supervisor import _WorkerInvoker  # noqa: PLC2701
        from blu_llm_service import get_model
        from agent_api.core.factory import get_mcp_executor
        _worker_invoker = _WorkerInvoker(llm=get_model(), mcp_executor=get_mcp_executor())
    return _worker_invoker

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_custom_routine(routine_id: str) -> bool:
    return bool(_UUID_RE.match(routine_id))


# ---------------------------------------------------------------------------
# DB helpers (sync, run via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _claim_sync(batch_size: int) -> list[dict]:
    return get_supabase_client().rpc("claim_routine_executions", {"p_batch_size": batch_size}).execute().data or []


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
    return db.table(table).select("name, steps").eq("id", routine_id).maybe_single().execute().data


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
    get_supabase_client().table("client_routine_executions").update(payload).eq("id", execution_id).execute()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def claim_dispatched_batch(batch_size: int = 10) -> list[dict]:
    return await asyncio.to_thread(_claim_sync, batch_size)


async def run_dispatched_executions(claimed: list[dict], context_service: ContextService) -> None:
    if not claimed:
        return

    for execution in claimed:
        exec_id = str(execution["id"])
        try:
            async with _mcp_semaphore:
                from agent_api.core.factory import get_mcp_manager
                get_mcp_manager().set_cliente_id(str(execution["client_id"]))
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
# Internal helpers
# ---------------------------------------------------------------------------


async def _execute_one(execution: dict, context_service: ContextService) -> tuple[str, str]:
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

    result_parts: list[str] = []
    last_worker_slug = ""

    for step in steps:
        step_n = step.get("step", 0)
        action: str = step.get("action", "")
        agent_slug: str = step.get("agent", "")
        session_id = f"routine:{exec_id}:step:{step_n}"

        task = (
            f"[ROUTINE TASK]\nRoutine: {routine_name}\n"
            f"Action: {action}\n"
            f"Input: {json.dumps(trigger_data, ensure_ascii=False)}"
        )

        result = await _invoke_worker(agent_slug, task, session_id, nome_empresa, context_service)

        step_summary = (result.summary or "")[:300]
        result_parts.append(f"Passo {step_n} ({action}): {step_summary}")
        last_worker_slug = agent_slug

        if result.error:
            logger.warning("[RoutineExecutor] Step %d of %s error: %s", step_n, exec_id, result.error)

    return "\n".join(result_parts) or "Concluído.", last_worker_slug


async def _invoke_worker(
    slug: str,
    task: str,
    session_id: str,
    nome_empresa: str,
    context_service: ContextService,
):
    from blu_agent_framework.registry import AgentTypeRegistry
    from blu_agent_framework.supervisor import WorkerResult

    cfg = AgentTypeRegistry.get(slug)
    if not cfg:
        return WorkerResult(summary="", worker_slug=slug, error=f"Unknown worker: {slug}")

    return await _get_worker_invoker().invoke(cfg, task, nome_empresa=nome_empresa, context_service=context_service)


async def _notify_client(execution: dict, result_text: str) -> None:
    client_id = str(execution["client_id"])
    routine_id = str(execution["routine_id"])

    row = await asyncio.to_thread(_fetch_client_routine_config_sync, client_id, routine_id)
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
            logger.info("[RoutineExecutor] Email notify queued for %s (not yet implemented)", client_id)

    logger.info("[RoutineExecutor] Completed: client=%s routine=%s channel=%s", client_id, routine_id, channel)
