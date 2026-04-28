"""
Twilio inbound webhook for the Tool Pool API — Phase 3A (P3.2) BLU-MVP-041.

When a supplier replies to an RFQ over WhatsApp, Twilio POSTs the message to
this endpoint. The router:

1. Validates the Twilio signature (HMAC-SHA1) when the signing token is set.
2. Normalizes the inbound phone number and resolves it to a row in
   `public.supplier_roster`.
3. Finds the most recent open RFQ (status='sent') for that supplier and
   tenant.
4. Calls :func:`parse_supplier_reply_core` to extract structured quote data
   and update `rfq_requests.response_data`.
5. Writes an audit_log entry and replies to the supplier with a short
   acknowledgement.

The endpoint is intentionally tolerant: an unknown number, an unknown RFQ,
or a parse failure do not return HTTP errors — Twilio retries aggressively
on 5xx, which would amplify failures. Instead we always return a valid
TwiML response and log the outcome.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Form, Header, Request, Response
from fastmcp.exceptions import ToolError

from tool_pool_api.server.tool_modules.rfq_whatsapp_module import (
    parse_supplier_reply_core,
)
from blu_agent_framework import record_audit
from blu_supabase_client import get_supabase_client
from blu_twilio_client.webhook import (
    create_twiml_response,
    validate_twilio_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["Twilio Webhooks"])


_PHONE_CLEAN_RE = re.compile(r"[\s\-()]+")


def _normalize_phone(value: str | None) -> str:
    """Strip whitespace/punctuation and the optional ``whatsapp:`` prefix."""
    if not value:
        return ""
    cleaned = _PHONE_CLEAN_RE.sub("", value.strip())
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned.split(":", 1)[1]
    return cleaned


def _phone_variants(phone: str) -> list[str]:
    """Return likely stored variants of a phone (with/without ``+``, etc.)."""
    if not phone:
        return []
    variants = {phone}
    if phone.startswith("+"):
        variants.add(phone[1:])
    else:
        variants.add("+" + phone)
    return list(variants)


def _lookup_supplier(db: Any, phone: str) -> dict[str, Any] | None:
    """Find a supplier roster row matching any of the phone variants."""
    variants = _phone_variants(phone)
    if not variants:
        return None
    try:
        resp = (
            db.table("supplier_roster")
            .select("id,client_id,name,contact_phone,is_active")
            .in_("contact_phone", variants)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("twilio_webhook: supplier lookup failed for %s", phone)
        return None
    rows = getattr(resp, "data", None) or []
    return dict(rows[0]) if rows else None


async def _resolve_client_id_for_phone(db: Any, to: str | None) -> str | None:
    """Map the Twilio destination phone (``To``) back to a tenant.

    Looks up the optional ``twilio_inbound_routes`` table (keyed by the
    Twilio number the message was sent to). Returns ``None`` if no mapping
    exists, in which case the webhook ack is generic.
    """
    if not to:
        return None
    normalized = _normalize_phone(to)
    try:
        resp = (
            db.table("twilio_inbound_routes")
            .select("client_id")
            .in_("twilio_number", _phone_variants(normalized))
            .limit(1)
            .execute()
        )
    except Exception:
        # Table may not exist yet in early dev environments — degrade
        # gracefully rather than failing the webhook.
        return None
    rows = getattr(resp, "data", None) or []
    return str(rows[0]["client_id"]) if rows else None


def _latest_open_rfq(db: Any, *, supplier_id: str, client_id: str) -> dict[str, Any] | None:
    """Return the most recent open RFQ for this (supplier, client)."""
    try:
        resp = (
            db.table("rfq_requests")
            .select("id,status,sent_at,deadline,communication_channel")
            .eq("supplier_id", supplier_id)
            .eq("client_id", client_id)
            .in_("status", ["sent", "pending"])
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("twilio_webhook: rfq lookup failed for supplier=%s", supplier_id)
        return None
    rows = getattr(resp, "data", None) or []
    return dict(rows[0]) if rows else None


def _record_audit(
    db: Any,
    *,
    client_id: str | None,
    action: str,
    payload: dict[str, Any],
    outcome: str = "success",
) -> None:
    """Domain wrapper around :func:`blu_agent_framework.record_audit` that
    fixes the ``rfq-agent`` / ``webhook`` defaults for Twilio inbound events.
    """
    record_audit(
        db,
        p_action=action,
        p_payload=payload,
        p_resource="rfq_requests",
        p_resource_id=payload.get("rfq_id"),
        p_actor_kind="webhook",
        p_agent_slug="rfq-agent",
        p_outcome=outcome,
        p_client_id=client_id,
    )


@router.post("/inbound", response_class=Response)
async def twilio_inbound(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    To: str | None = Form(None),
    MessageSid: str | None = Form(None),
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
) -> Response:
    """Twilio inbound endpoint for supplier WhatsApp replies."""

    # 1) Optional signature validation. Skip when no token configured (dev).
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if auth_token:
        # Twilio's signature is computed against the URL it called, including
        # protocol+host+path, plus a flat dict of form fields.
        form = await request.form()
        flat: dict[str, str] = {k: str(v) for k, v in form.items()}
        url = str(request.url)
        if not validate_twilio_signature(auth_token, url, flat, x_twilio_signature):
            logger.warning("twilio_webhook: invalid signature, dropping message")
            return Response(content=create_twiml_response(), media_type="application/xml")

    db = get_supabase_client()
    phone = _normalize_phone(From)

    supplier = _lookup_supplier(db, phone)
    if supplier is None:
        # Phase 3B fallback: store as a consumer inbox message so the
        # Comercial agent / dashboard Inbox can pick it up.
        client_id = await _resolve_client_id_for_phone(db, To)
        if client_id is None:
            logger.info(
                "twilio_webhook: unmatched phone %s and no client mapping for To=%s",
                phone, To,
            )
            return Response(
                content=create_twiml_response(
                    "Mensagem recebida. Vamos retornar em breve."
                ),
                media_type="application/xml",
            )

        from tool_pool_api.server.tool_modules.consumer_inbox_helpers import (
            insert_inbound_message,
            upsert_consumer_contact,
        )

        contact = upsert_consumer_contact(
            db,
            client_id=client_id,
            channel="whatsapp",
            external_id=phone,
        )
        if contact is None:
            logger.warning("twilio_webhook: failed to upsert consumer contact for %s", phone)
            return Response(
                content=create_twiml_response(
                    "Mensagem recebida. Vamos retornar em breve."
                ),
                media_type="application/xml",
            )

        msg_id = insert_inbound_message(
            db,
            client_id=client_id,
            contact_id=contact["id"],
            channel="whatsapp",
            body=Body,
            external_id=MessageSid,
        )
        _record_audit(
            db,
            client_id=client_id,
            action="inbox.consumer_message_received",
            payload={
                "contact_id": contact["id"],
                "message_id": msg_id,
                "phone": phone,
                "message_sid": MessageSid,
            },
            outcome="success",
        )
        return Response(
            content=create_twiml_response(
                "Recebemos sua mensagem. Em breve retornaremos!"
            ),
            media_type="application/xml",
        )

    rfq = _latest_open_rfq(db, supplier_id=supplier["id"], client_id=supplier["client_id"])
    if rfq is None:
        logger.info(
            "twilio_webhook: supplier %s has no open RFQ — ignoring",
            supplier.get("name"),
        )
        _record_audit(
            db,
            client_id=supplier["client_id"],
            action="rfq.inbound_no_open",
            payload={"supplier_id": supplier["id"], "phone": phone, "message_sid": MessageSid},
            outcome="partial",
        )
        return Response(
            content=create_twiml_response(
                "Recebemos sua mensagem, mas não há cotação aberta no momento. Entraremos em contato."
            ),
            media_type="application/xml",
        )

    try:
        result = await parse_supplier_reply_core(
            cliente_id=str(supplier["client_id"]),
            rfq_id=rfq["id"],
            reply_text=Body,
        )
    except ToolError as exc:
        logger.warning("twilio_webhook: parse failed for rfq=%s: %s", rfq["id"], exc)
        _record_audit(
            db,
            client_id=str(supplier["client_id"]),
            action="rfq.inbound_parse_failed",
            payload={
                "rfq_id": rfq["id"],
                "supplier_id": supplier["id"],
                "error": str(exc),
                "message_sid": MessageSid,
            },
            outcome="failure",
        )
        return Response(
            content=create_twiml_response(
                "Recebemos sua resposta, mas tivemos dificuldade em processá-la. Vamos revisar manualmente."
            ),
            media_type="application/xml",
        )

    confidence = result.get("confidence", "unknown")
    items_parsed = result.get("items_parsed", 0)
    _record_audit(
        db,
        client_id=str(supplier["client_id"]),
        action="rfq.supplier_reply_parsed",
        payload={
            "rfq_id": rfq["id"],
            "supplier_id": supplier["id"],
            "confidence": confidence,
            "items_parsed": items_parsed,
            "message_sid": MessageSid,
            "received_at": datetime.now(UTC).isoformat(),
        },
        outcome="success" if confidence != "failed" else "failure",
    )

    if confidence == "failed":
        ack = (
            "Recebemos sua resposta. Não conseguimos extrair os preços automaticamente; "
            "nossa equipe vai conferir."
        )
    else:
        ack = (
            f"Resposta recebida e processada ({items_parsed} item(ns)). Obrigado!"
        )
    return Response(content=create_twiml_response(ack), media_type="application/xml")


__all__ = ["router"]
