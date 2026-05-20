"""Phase 3B (C3.2) — Comercial draft & send tools.

Two ctx-free cores plus their MCP wrappers:

- :func:`draft_consumer_reply_core` — uses an LLM (FAST tier) to compose a
  short reply grounded in the thread's recent messages. Persists the draft
  as a ``consumer_messages`` row with ``status='draft'`` so the dashboard
  can render and edit it.
- :func:`send_consumer_reply_core` — promotes a draft. Reads the tenant's
  approval policy via :func:`blu_agent_framework.approval.resolve_policy`
  and either:
    • enqueues an ``approval_requests`` row (status ``pending_approval``)
      — the actual dispatch happens once an approver flips the status
      to ``approved`` (a follow-up worker reads ``approved`` rows and
      sends them).
    • dispatches immediately via Twilio when the policy says so
      (typical for BASIC tenants where chat elicitation is the approval).

Both cores write ``audit_log`` entries.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastmcp.exceptions import ToolError

from blu_agent_framework import record_audit as _record_audit
from blu_agent_framework.approval import ApprovalEngine, resolve_policy
from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


_DRAFT_SYSTEM_PROMPT = """\
Você é a assistente de relacionamento de uma SMB brasileira. Componha uma
resposta curta, cordial e útil à última mensagem do cliente, em português
do Brasil. Use no máximo 3 frases. Não invente informações que você não
viu na conversa. Se faltar contexto, peça educadamente o que precisa.
"""


def _fmt_thread_for_prompt(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for msg in messages[-12:]:  # cap context
        prefix = "Cliente" if msg.get("direction") == "inbound" else "Loja"
        body = (msg.get("body") or "").strip()
        if body:
            lines.append(f"{prefix}: {body}")
    return "\n".join(lines)


async def _generate_draft_with_llm(thread_text: str, *, hint: str | None = None) -> str:
    """Call the FAST-tier model to produce a reply. Returns plain text."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from blu_llm_service import get_model
    from blu_llm_service.client import ModelTier

    user_payload = thread_text
    if hint:
        user_payload = f"{thread_text}\n\nObservação do operador: {hint}"

    model = get_model(tier=ModelTier.FAST, tags=["comercial", "consumer-draft"])
    response = await model.ainvoke([
        SystemMessage(content=_DRAFT_SYSTEM_PROMPT),
        HumanMessage(content=user_payload),
    ])
    return (response.content or "").strip()


def _load_thread_messages(db: Any, *, contact_id: str, client_id: str) -> list[dict[str, Any]]:
    """Read the conversation history (oldest → newest)."""
    resp = (
        db.table("consumer_messages")
        .select("id,direction,status,body,created_at")
        .eq("client_id", client_id)
        .eq("contact_id", contact_id)
        .order("created_at", desc=False)
        .limit(50)
        .execute()
    )
    return list(getattr(resp, "data", None) or [])


async def draft_consumer_reply_core(
    *,
    client_id: str,
    contact_id: str,
    hint: str | None = None,
) -> dict[str, Any]:
    """Compose a draft reply and persist it as a ``consumer_messages`` row.

    Returns ``{"message_id", "draft_text", "channel"}``.
    """
    if not client_id:
        raise ToolError("Missing client_id")
    if not contact_id:
        raise ToolError("Missing contact_id")

    db = get_supabase_client()

    contact_resp = (
        db.table("consumer_contacts")
        .select("id,client_id,channel,external_id,display_name")
        .eq("id", contact_id)
        .eq("client_id", client_id)
        .single()
        .execute()
    )
    contact = getattr(contact_resp, "data", None)
    if not contact:
        raise ToolError("Contact not found or not owned")

    history = _load_thread_messages(db, contact_id=contact_id, client_id=client_id)
    if not history:
        raise ToolError("Thread has no messages — nothing to reply to")

    thread_text = _fmt_thread_for_prompt(history)
    try:
        draft_text = await _generate_draft_with_llm(thread_text, hint=hint)
    except Exception as exc:
        logger.exception("draft_consumer_reply: LLM generation failed")
        raise ToolError(f"Falha ao gerar rascunho: {exc}") from exc

    if not draft_text:
        raise ToolError("LLM returned an empty draft")

    insert = (
        db.table("consumer_messages")
        .insert({
            "client_id":  client_id,
            "contact_id": contact_id,
            "channel":    contact["channel"],
            "direction":  "outbound",
            "status":     "draft",
            "body":       draft_text,
            "metadata":   {"generated_by": "comercial-agent", "hint": hint},
        })
        .execute()
    )
    rows = getattr(insert, "data", None) or []
    if not rows:
        raise ToolError("Failed to persist draft message")

    msg_id = rows[0]["id"]
    _record_audit(
        db,
        p_action="comercial.draft_created",
        p_payload={"message_id": msg_id, "contact_id": contact_id},
        p_resource="consumer_messages",
        p_resource_id=msg_id,
        p_actor_kind="agent",
        p_agent_slug="comercial-agent",
        p_outcome="success",
        p_client_id=client_id,
    )

    return {
        "message_id": msg_id,
        "draft_text": draft_text,
        "channel": contact["channel"],
    }


async def send_consumer_reply_core(
    *,
    client_id: str,
    message_id: str,
    edited_body: str | None = None,
) -> dict[str, Any]:
    """Promote a draft to either pending_approval or approved+sent.

    Returns one of:
      ``{"status": "pending_approval", "approval_id": ...}``
      ``{"status": "sent", "external_id": ...}``
    """
    if not client_id or not message_id:
        raise ToolError("Missing client_id or message_id")

    db = get_supabase_client()
    msg_resp = (
        db.table("consumer_messages")
        .select("id,client_id,contact_id,channel,status,body")
        .eq("id", message_id)
        .eq("client_id", client_id)
        .single()
        .execute()
    )
    msg = getattr(msg_resp, "data", None)
    if not msg:
        raise ToolError("Message not found or not owned")
    if msg["status"] not in ("draft", "pending_approval"):
        raise ToolError(f"Message in status {msg['status']} cannot be sent")

    if edited_body and edited_body.strip():
        body = edited_body.strip()
        db.table("consumer_messages").update({"body": body}).eq("id", message_id).execute()
    else:
        body = msg["body"]

    contact_resp = (
        db.table("consumer_contacts")
        .select("external_id,channel,display_name")
        .eq("id", msg["contact_id"])
        .single()
        .execute()
    )
    contact = getattr(contact_resp, "data", None)
    if not contact:
        raise ToolError("Contact missing for message")

    decision = resolve_policy(
        client_id=client_id,
        agent_slug="comercial-agent",
        action="send_consumer_reply",
        payload={"message_id": message_id, "channel": msg["channel"]},
        supabase=db,
    )

    if decision.requires_async_approval:
        # Mark message pending and enqueue an approval row.
        db.table("consumer_messages").update(
            {"status": "pending_approval"}
        ).eq("id", message_id).execute()

        engine = ApprovalEngine(db)
        request = engine.request(
            agent_slug="comercial-agent",
            action="send_consumer_reply",
            payload={
                "message_id":  message_id,
                "contact_id":  msg["contact_id"],
                "channel":     msg["channel"],
                "preview":     body[:160],
            },
            routed_to_role=decision.routed_role,
            sla_hours=decision.sla_hours,
        )
        _record_audit(
            db,
            p_action="comercial.send_queued",
            p_payload={"message_id": message_id, "approval_id": request.id, "reason": decision.reason},
            p_resource="consumer_messages",
            p_resource_id=message_id,
            p_actor_kind="agent",
            p_agent_slug="comercial-agent",
            p_outcome="success",
            p_client_id=client_id,
        )
        return {"status": "pending_approval", "approval_id": request.id}

    # Direct send — chat elicitation has already approved.
    return await _dispatch_consumer_message(
        db,
        client_id=client_id,
        message_id=message_id,
        channel=msg["channel"],
        external_to=contact["external_id"],
        body=body,
    )


async def _dispatch_consumer_message(
    db: Any,
    *,
    client_id: str,
    message_id: str,
    channel: str,
    external_to: str,
    body: str,
) -> dict[str, Any]:
    """Send the message via the right channel and update the row."""
    if channel == "whatsapp":
        from blu_twilio_client import TwilioClient
        from blu_twilio_client.config import get_twilio_settings

        twilio = TwilioClient(get_twilio_settings())
        try:
            sid = twilio.send_whatsapp(to=external_to, body=body)
        except Exception as exc:
            logger.exception("send_consumer_reply: twilio failure")
            db.table("consumer_messages").update(
                {"status": "failed", "failure_reason": str(exc)[:500]}
            ).eq("id", message_id).execute()
            raise ToolError(f"Falha ao enviar pelo WhatsApp: {exc}") from exc

        db.table("consumer_messages").update(
            {
                "status":      "sent",
                "external_id": sid,
                "sent_at":     datetime.now(UTC).isoformat(),
            }
        ).eq("id", message_id).execute()

        _record_audit(
            db,
            p_action="comercial.message_sent",
            p_payload={"message_id": message_id, "twilio_sid": sid, "channel": channel},
            p_resource="consumer_messages",
            p_resource_id=message_id,
            p_actor_kind="user",
            p_agent_slug="comercial-agent",
            p_outcome="success",
            p_client_id=client_id,
        )
        return {"status": "sent", "external_id": sid}

    # Gmail / other channels — placeholder until C3.4.
    raise ToolError(f"Channel {channel!r} not yet supported for outbound")


__all__ = [
    "draft_consumer_reply_core",
    "send_consumer_reply_core",
]
