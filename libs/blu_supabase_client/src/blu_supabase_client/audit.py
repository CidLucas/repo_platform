"""
Audit log helper — Phase 0 / F0.4.

Thin wrapper around the ``public.record_audit(...)`` RPC. Every mutating
MCP tool, scheduled job, or webhook ingest should call :func:`record_audit`
exactly once per state change. The RPC is SECURITY DEFINER and resolves
``client_id`` from the caller's JWT (or accepts an explicit override for
service-role callers like cron workers).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

ActorKind = Literal["user", "agent", "system", "cron", "webhook"]
Outcome = Literal["success", "failure", "partial", "pending"]


class AuditError(RuntimeError):
    """Raised when the audit RPC fails."""


def record_audit(
    *,
    action: str,
    payload: dict[str, Any] | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    actor_kind: ActorKind = "user",
    agent_slug: str | None = None,
    decision: str | None = None,
    outcome: Outcome = "success",
    session_id: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    client_id: str | None = None,
    supabase: Any | None = None,
    raise_on_error: bool = False,
) -> int | None:
    """Append a row to ``public.audit_log`` via the canonical RPC.

    Args:
        action: Required action verb, e.g. ``"po.created"``, ``"rfq.dispatched"``.
        payload: Arbitrary JSON context (sanitize PII before passing).
        resource / resource_id: Pointer to the affected row.
        actor_kind: Who performed the action.
        agent_slug: Originating agent if applicable.
        decision: Optional decision label (e.g. for approvals).
        outcome: Final outcome.
        session_id / trace_id / span_id: Observability cross-links.
        client_id: Required for service-role / cron callers; ignored when
            the JWT already carries a tenant.
        supabase: Optional supabase client (defaults to the singleton).
        raise_on_error: If True, surface RPC failures. Defaults to False so
            audit failures never break the parent operation — they are logged.

    Returns:
        The new ``audit_log.id`` (bigint) on success, ``None`` on failure
        when ``raise_on_error`` is False.
    """
    if not action or not action.strip():
        raise ValueError("action is required")

    if supabase is None:
        from blu_supabase_client.client import get_supabase_client

        supabase = get_supabase_client()

    params: dict[str, Any] = {
        "p_action": action,
        "p_payload": payload or {},
        "p_resource": resource,
        "p_resource_id": resource_id,
        "p_actor_kind": actor_kind,
        "p_agent_slug": agent_slug,
        "p_decision": decision,
        "p_outcome": outcome,
        "p_session_id": session_id,
        "p_trace_id": trace_id,
        "p_span_id": span_id,
        "p_client_id": client_id,
    }

    try:
        resp = supabase.rpc("record_audit", params).execute()
    except Exception as exc:
        logger.warning("record_audit RPC failed (action=%s): %s", action, exc)
        if raise_on_error:
            raise AuditError(f"record_audit RPC failed: {exc}") from exc
        return None

    data = getattr(resp, "data", None)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        data = data.get("record_audit") or next(iter(data.values()), None)
    try:
        return int(data) if data is not None else None
    except (TypeError, ValueError):
        return None


__all__ = ["AuditError", "ActorKind", "Outcome", "record_audit"]
