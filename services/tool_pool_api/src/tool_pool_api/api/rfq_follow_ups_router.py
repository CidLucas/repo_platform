"""
RFQ follow-up dispatcher — Phase 3A (P3.3) BLU-MVP-042.

Internal endpoint scanned by pg_cron every 30 minutes. For every RFQ that:

- has ``status = 'sent'`` and ``communication_channel = 'whatsapp'``,
- has a non-null ``deadline``,
- has a remaining time-to-deadline that crosses one of the follow-up
  thresholds (T-12h or T-2h),
- has a low enough ``follow_up_count`` to receive the next reminder,

we dispatch a short WhatsApp reminder via :class:`vizu_twilio_client.TwilioClient`,
increment ``follow_up_count``, and write an ``audit_log`` entry.

The endpoint is idempotent: each (rfq_id, milestone) is dispatched at most
once thanks to the ``follow_up_count`` gate.

Auth: a shared secret in the ``Authorization: Bearer <token>`` header. The
expected token is read from ``RFQ_FOLLOW_UPS_TOKEN`` (or
``DAILY_INSIGHTS_RUNNER_TOKEN`` as a fallback) so cron operators can re-use
the same shared secret.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from vizu_agent_framework import record_audit
from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/rfq", tags=["RFQ Internal"])


# Threshold table: hours-to-deadline → follow-up step. We dispatch one
# reminder per crossed threshold, gated by ``follow_up_count``:
#
#   follow_up_count == 0  → eligible for the T-12h reminder
#   follow_up_count == 1  → eligible for the T-2h reminder
#   follow_up_count >= 2  → no further reminders
#
# Each tier expects ``hours_lower < remaining_hours <= hours_upper``.
_THRESHOLDS = (
    {"step": 1, "hours_lower": 2.0, "hours_upper": 12.0, "label": "12h"},
    {"step": 2, "hours_lower": 0.0, "hours_upper": 2.0, "label": "2h"},
)


def _verify_token(authorization: str | None) -> None:
    expected = (
        os.getenv("RFQ_FOLLOW_UPS_TOKEN")
        or os.getenv("DAILY_INSIGHTS_RUNNER_TOKEN")
    )
    if not expected:
        return  # No token configured → endpoint is open (dev only).
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def _hours_until(deadline_iso: str, *, now: datetime) -> float | None:
    try:
        dl = datetime.fromisoformat(str(deadline_iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dl.tzinfo is None:
        dl = dl.replace(tzinfo=UTC)
    return (dl - now).total_seconds() / 3600.0


def _resolve_threshold(remaining_h: float, follow_up_count: int) -> dict[str, Any] | None:
    """Return the threshold this RFQ is eligible for, or ``None``."""
    for tier in _THRESHOLDS:
        if tier["step"] <= follow_up_count:
            continue  # already sent at this tier
        if tier["hours_lower"] < remaining_h <= tier["hours_upper"]:
            return tier
    return None


def _build_follow_up_text(*, supplier_name: str, items_count: int, label: str) -> str:
    if label == "12h":
        head = "Olá! Faltam 12 horas para o fim do prazo desta cotação."
    else:
        head = "Olá! Faltam 2 horas para encerrarmos esta cotação."
    return (
        f"{head}\n\n"
        f"Sua resposta com preços e prazos para os {items_count} item(ns) é importante "
        f"para fecharmos o pedido com {supplier_name}. Responda esta mensagem com sua proposta. Obrigado!"
    )


def _record_audit(
    db: Any,
    *,
    client_id: str,
    rfq_id: str,
    milestone: str,
    outcome: str,
    payload: dict[str, Any],
) -> None:
    """Domain wrapper around :func:`vizu_agent_framework.record_audit` that
    fixes the ``rfq-agent`` / ``cron`` defaults for follow-up dispatches.
    """
    record_audit(
        db,
        p_action=f"rfq.follow_up.{milestone}",
        p_payload=payload,
        p_resource="rfq_requests",
        p_resource_id=rfq_id,
        p_actor_kind="cron",
        p_agent_slug="rfq-agent",
        p_outcome=outcome,
        p_client_id=client_id,
    )


@router.post("/follow-ups/run")
async def run_follow_ups(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Scan and dispatch due follow-ups. Returns a small summary."""

    _verify_token(authorization)

    db = get_supabase_client()
    now = datetime.now(UTC)

    # Pull a small batch — pg_cron runs us every 30 min, so each tick should
    # be cheap. We scan only WhatsApp-channel RFQs still awaiting a reply.
    try:
        resp = (
            db.table("rfq_requests")
            .select(
                "id,client_id,supplier_id,items,deadline,follow_up_count,"
                "communication_channel,status,"
                "supplier_roster(name,contact_phone,is_active)"
            )
            .eq("status", "sent")
            .eq("communication_channel", "whatsapp")
            .not_.is_("deadline", "null")
            .lt("follow_up_count", len(_THRESHOLDS))
            .limit(200)
            .execute()
        )
    except Exception:
        logger.exception("rfq.follow_up: scan failed")
        raise HTTPException(status_code=500, detail="scan failed")

    rows = getattr(resp, "data", None) or []
    summary = {"scanned": len(rows), "dispatched": 0, "skipped": 0, "errors": 0, "by_milestone": {}}

    if not rows:
        return summary

    # Lazy imports — keeps the endpoint cheap when nothing is due.
    from vizu_twilio_client import TwilioClient
    from vizu_twilio_client.config import get_twilio_settings

    twilio = TwilioClient(get_twilio_settings())

    for row in rows:
        rfq_id = row.get("id")
        deadline = row.get("deadline")
        follow_up_count = int(row.get("follow_up_count") or 0)
        supplier = row.get("supplier_roster") or {}
        phone = supplier.get("contact_phone")

        if not phone or not supplier.get("is_active", True):
            summary["skipped"] += 1
            continue

        remaining = _hours_until(deadline, now=now)
        if remaining is None:
            summary["skipped"] += 1
            continue
        if remaining <= 0:
            # Deadline passed; outside the cron's responsibility.
            summary["skipped"] += 1
            continue

        tier = _resolve_threshold(remaining, follow_up_count)
        if tier is None:
            summary["skipped"] += 1
            continue

        items = row.get("items") or []
        body = _build_follow_up_text(
            supplier_name=supplier.get("name", "Fornecedor"),
            items_count=len(items),
            label=tier["label"],
        )

        try:
            sid = twilio.send_whatsapp(to=phone, body=body)
        except Exception as exc:  # pragma: no cover
            logger.warning("rfq.follow_up: twilio send failed for %s: %s", rfq_id, exc)
            summary["errors"] += 1
            _record_audit(
                db,
                client_id=str(row["client_id"]),
                rfq_id=rfq_id,
                milestone=tier["label"],
                outcome="failure",
                payload={"error": str(exc), "phone": phone},
            )
            continue

        try:
            db.table("rfq_requests").update(
                {
                    "follow_up_count": tier["step"],
                    "updated_at": now.isoformat(),
                }
            ).eq("id", rfq_id).execute()
        except Exception:
            logger.exception("rfq.follow_up: failed to bump follow_up_count for %s", rfq_id)
            summary["errors"] += 1
            continue

        summary["dispatched"] += 1
        summary["by_milestone"][tier["label"]] = (
            summary["by_milestone"].get(tier["label"], 0) + 1
        )
        _record_audit(
            db,
            client_id=str(row["client_id"]),
            rfq_id=rfq_id,
            milestone=tier["label"],
            outcome="success",
            payload={
                "message_sid": sid,
                "remaining_hours": round(remaining, 2),
                "follow_up_count": tier["step"],
            },
        )

    logger.info("rfq.follow_up: %s", summary)
    return summary


__all__ = ["router"]
