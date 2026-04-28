"""Centralized audit-log helper.

Every MCP tool / router / cron job that mutates tenant state must write an
``audit_log`` row via the ``record_audit`` Postgres RPC. This module provides
the single canonical client-side wrapper used across all services, replacing
the ad-hoc ``_record_audit`` helpers that previously lived in each module.

Usage
-----
>>> from blu_agent_framework import record_audit
>>> record_audit(
...     db,
...     p_action="rfq.supplier_reply_parsed",
...     p_payload={"rfq_id": "..."},
...     p_resource="rfq_requests",
...     p_resource_id="...",
...     p_actor_kind="webhook",
...     p_agent_slug="rfq-agent",
...     p_outcome="success",
...     p_client_id="...",
... )

The helper is best-effort: failures are logged at WARNING level but never
raised, since audit-logging must never break a user-visible flow.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_audit(db: Any, **rpc_kwargs: Any) -> None:
    """Best-effort write to the ``audit_log`` table via ``record_audit`` RPC.

    Parameters
    ----------
    db:
        A Supabase client (sync or async-compatible) exposing
        ``db.rpc(name, params).execute()``.
    **rpc_kwargs:
        Parameters forwarded verbatim to the RPC. Conventionally use the
        ``p_action``, ``p_payload``, ``p_resource``, ``p_resource_id``,
        ``p_actor_kind``, ``p_agent_slug``, ``p_outcome``, ``p_client_id``
        keys defined by the ``record_audit`` Postgres function.
    """
    try:
        db.rpc("record_audit", rpc_kwargs).execute()
    except Exception:  # pragma: no cover - best effort
        logger.warning(
            "record_audit: failed to write audit_log entry (action=%s)",
            rpc_kwargs.get("p_action"),
            exc_info=True,
        )
