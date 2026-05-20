"""Phase 3B (C3.2) — dispatch approved consumer messages.

Polled either by pg_cron (preferred) or by a sidecar worker. Scans
``consumer_messages`` for ``status = 'approved'`` rows (the Approval
Engine trigger flips them there once an approver decides) and sends
them via the appropriate channel, transitioning to ``sent`` or
``failed``.

Auth: shared bearer secret in ``CONSUMER_DISPATCH_TOKEN``.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from blu_agent_framework import record_audit as _record_audit
from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/inbox", tags=["Inbox Internal"])


def _verify_token(authorization: str | None) -> None:
    expected = os.getenv("CONSUMER_DISPATCH_TOKEN")
    if not expected:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.post("/dispatch-approved")
async def dispatch_approved(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Send up to 50 approved consumer messages."""

    _verify_token(authorization)

    db = get_supabase_client()
    try:
        resp = (
            db.table("consumer_messages")
            .select(
                "id,client_id,contact_id,channel,body,"
                "consumer_contacts(external_id)"
            )
            .eq("status", "approved")
            .limit(50)
            .execute()
        )
    except Exception:
        logger.exception("inbox.dispatch: scan failed")
        raise HTTPException(status_code=500, detail="scan failed")

    rows = getattr(resp, "data", None) or []
    summary = {"scanned": len(rows), "sent": 0, "failed": 0}
    if not rows:
        return summary

    twilio = None  # lazy

    for row in rows:
        msg_id = row["id"]
        channel = row.get("channel")
        contact = row.get("consumer_contacts") or {}
        external_to = contact.get("external_id")

        if channel != "whatsapp" or not external_to:
            db.table("consumer_messages").update(
                {"status": "failed", "failure_reason": "channel not supported / missing recipient"}
            ).eq("id", msg_id).execute()
            summary["failed"] += 1
            continue

        if twilio is None:
            from blu_twilio_client import TwilioClient
            from blu_twilio_client.config import get_twilio_settings

            twilio = TwilioClient(get_twilio_settings())

        try:
            sid = twilio.send_whatsapp(to=external_to, body=row["body"])
        except Exception as exc:
            logger.warning("inbox.dispatch: send failed for %s: %s", msg_id, exc)
            db.table("consumer_messages").update(
                {"status": "failed", "failure_reason": str(exc)[:500]}
            ).eq("id", msg_id).execute()
            _record_audit(
                db,
                p_action="comercial.message_send_failed",
                p_payload={"message_id": msg_id, "error": str(exc)},
                p_resource="consumer_messages",
                p_resource_id=msg_id,
                p_actor_kind="cron",
                p_agent_slug="comercial-agent",
                p_outcome="failure",
                p_client_id=str(row["client_id"]),
            )
            summary["failed"] += 1
            continue

        db.table("consumer_messages").update(
            {
                "status":      "sent",
                "external_id": sid,
                "sent_at":     datetime.now(UTC).isoformat(),
            }
        ).eq("id", msg_id).execute()

        _record_audit(
            db,
            p_action="comercial.message_sent",
            p_payload={"message_id": msg_id, "twilio_sid": sid, "channel": channel},
            p_resource="consumer_messages",
            p_resource_id=msg_id,
            p_actor_kind="cron",
            p_agent_slug="comercial-agent",
            p_outcome="success",
            p_client_id=str(row["client_id"]),
        )
        summary["sent"] += 1

    logger.info("inbox.dispatch: %s", summary)
    return summary


__all__ = ["router"]
