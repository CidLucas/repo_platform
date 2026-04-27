"""Phase 3B (C3.1) — consumer inbox helpers shared between webhook and tools.

Centralizes the small set of helpers used by both the Twilio fallback
(when an inbound WhatsApp message doesn't match a supplier) and the
``consumer_inbox_module`` MCP tools.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def upsert_consumer_contact(
    db: Any,
    *,
    client_id: str,
    channel: str,
    external_id: str,
    display_name: str | None = None,
) -> dict[str, Any] | None:
    """Insert-if-missing a ``consumer_contacts`` row and return it."""
    if not external_id:
        return None
    try:
        existing = (
            db.table("consumer_contacts")
            .select("id,client_id,channel,external_id,display_name")
            .eq("client_id", client_id)
            .eq("channel", channel)
            .eq("external_id", external_id)
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if rows:
            return dict(rows[0])
        ins = (
            db.table("consumer_contacts")
            .insert(
                {
                    "client_id": client_id,
                    "channel": channel,
                    "external_id": external_id,
                    "display_name": display_name,
                }
            )
            .execute()
        )
        rows = getattr(ins, "data", None) or []
        return dict(rows[0]) if rows else None
    except Exception:
        logger.exception(
            "upsert_consumer_contact: failed for client=%s channel=%s",
            client_id, channel,
        )
        return None


def insert_inbound_message(
    db: Any,
    *,
    client_id: str,
    contact_id: str,
    channel: str,
    body: str,
    external_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Insert an inbound consumer message; return its id."""
    try:
        resp = (
            db.table("consumer_messages")
            .insert(
                {
                    "client_id": client_id,
                    "contact_id": contact_id,
                    "channel": channel,
                    "direction": "inbound",
                    "status": "received",
                    "body": body,
                    "external_id": external_id,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return rows[0].get("id") if rows else None
    except Exception:
        logger.exception("insert_inbound_message: failed")
        return None


__all__ = ["upsert_consumer_contact", "insert_inbound_message"]
