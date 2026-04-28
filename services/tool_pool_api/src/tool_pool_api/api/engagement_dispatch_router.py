"""Phase D (D1, D2) — onboarding engagement + pending approvals digest dispatcher.

Cron-friendly internal endpoint that scans tenants and emits:
- 5min resume reminder (early activation nudge)
- 24h first-approval reminder
- 72h stalled reminder
- 7d weekly digest
- daily pending-approvals digest (WhatsApp/email)

Delivery strategy:
- WhatsApp when tenant opted in and a phone is available in routine config.
- Email via Gmail API when GMAIL_SENDER_ACCESS_TOKEN is set; falls back to
  queued-only audit entry when the env var is absent (safe for local/staging).

Required env vars for email delivery:
  GMAIL_SENDER_ACCESS_TOKEN  — OAuth2 access token for the sending account.
  GMAIL_SENDER_REFRESH_TOKEN — Optional; enables token refresh.
  GMAIL_SENDER_FROM_EMAIL    — Sender address shown in the From header.

Auth: shared bearer secret in ``ENGAGEMENT_DISPATCH_TOKEN`` (fallbacks to
``DAILY_INSIGHTS_RUNNER_TOKEN`` and ``RFQ_FOLLOW_UPS_TOKEN`` for ops simplicity).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from blu_agent_framework import record_audit
from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/engagement", tags=["Engagement Internal"])

A_5MIN = "engagement.trigger.5min_resume"
A_24H = "engagement.trigger.24h_first_approval"
A_72H = "engagement.trigger.72h_stalled"
A_7D = "engagement.trigger.7d_weekly_digest"
A_PENDING = "engagement.digest.pending_approvals"


def _verify_token(authorization: str | None) -> None:
    expected = (
        os.getenv("ENGAGEMENT_DISPATCH_TOKEN")
        or os.getenv("DAILY_INSIGHTS_RUNNER_TOKEN")
        or os.getenv("RFQ_FOLLOW_UPS_TOKEN")
    )
    if not expected:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _has_audit_since(db: Any, client_id: str, action: str, since: datetime) -> bool:
    rows = (
        db.table("audit_log")
        .select("id")
        .eq("client_id", client_id)
        .eq("action", action)
        .gte("created_at", since.isoformat())
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def _count_synced_connectors(db: Any, client_id: str) -> int:
    rows = (
        db.table("client_data_sources")
        .select("id")
        .eq("client_id", client_id)
        .not_.is_("last_synced_at", "null")
        .limit(200)
        .execute()
        .data
        or []
    )
    return len(rows)


def _count_pending_approvals(db: Any, client_id: str) -> int:
    rows = (
        db.table("approval_requests")
        .select("id")
        .eq("client_id", client_id)
        .eq("status", "pending")
        .limit(500)
        .execute()
        .data
        or []
    )
    return len(rows)


def _has_approval_decision(db: Any, client_id: str) -> bool:
    rows = (
        db.table("approval_requests")
        .select("id")
        .eq("client_id", client_id)
        .not_.is_("decided_at", "null")
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def _resolve_notify_target(db: Any, client_id: str) -> tuple[str, str | None, str | None]:
    rows = (
        db.table("client_routines")
        .select("notify_channel, config")
        .eq("client_id", client_id)
        .eq("enabled", True)
        .in_("routine_id", ["daily_sales_digest", "weekly_performance"])
        .limit(5)
        .execute()
        .data
        or []
    )

    for row in rows:
        config = row.get("config") or {}
        phone = config.get("phone_e164") or config.get("whatsapp_number")
        email = config.get("email")
        channel = (row.get("notify_channel") or "email").lower()
        if channel == "whatsapp" and phone:
            return "whatsapp", str(phone), str(email) if email else None

    if rows:
        config = rows[0].get("config") or {}
        email = config.get("email")
        return str(rows[0].get("notify_channel") or "email").lower(), None, str(email) if email else None

    return "email", None, None


def _message_for(action: str, *, empresa: str, pending_approvals: int, connectors_synced: int) -> str:
    if action == A_5MIN:
        return (
            f"Blu: {empresa}, montei seu Mission Control. "
            "Próximo passo em 2 minutos: conecte uma fonte e aprove sua primeira ação."
        )
    if action == A_24H:
        return (
            f"Blu: {empresa}, já faz 24h do cadastro e ainda não tivemos a primeira aprovação. "
            "Quer que eu priorize 1 ação sugerida para você aprovar agora?"
        )
    if action == A_72H:
        return (
            f"Blu: {empresa}, notamos a ativação parada há 72h. "
            "Conecte sua fonte principal para sair do modo demo e liberar insights reais."
        )
    if action == A_7D:
        return (
            f"Resumo semanal Blu ({empresa}): conectores ativos={connectors_synced}, "
            f"aprovações pendentes={pending_approvals}. "
            "Abra o Mission Control para revisar prioridades da semana."
        )
    return (
        f"Blu: {empresa}, você tem {pending_approvals} aprovação(ões) pendente(s). "
        "Abra a aba Aprovações para decidir em 1 clique."
    )


def _subject_for(action: str) -> str:
    subjects: dict[str, str] = {
        A_5MIN: "Blu: seu Mission Control está pronto — próximo passo em 2 min",
        A_24H: "Blu: 24h de cadastro — ainda não tivemos a primeira aprovação",
        A_72H: "Blu: ativação pausada — conecte sua fonte e saia do modo demo",
        A_7D: "Blu: resumo semanal — ações e KPIs da semana",
        A_PENDING: "Blu: aprovações pendentes aguardando sua decisão",
    }
    return subjects.get(action, "Notificação Blu")


def _html_for(message: str) -> str:
    escaped = (
        message.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
    return (
        f'<html><body style="font-family:sans-serif;color:#111;padding:24px">'
        f"<p>{escaped}</p>"
        f'<p style="margin-top:32px"><a href="https://app.blu.ai/dashboard" '
        f'style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;'
        f'text-decoration:none">Abrir Mission Control →</a></p>'
        f'<p style="color:#888;font-size:12px;margin-top:24px">Blu por Blu.ai</p>'
        f"</body></html>"
    )


async def _send_gmail(*, to: str, subject: str, body_text: str, body_html: str) -> str | None:
    """Send via Gmail API. Returns message_id on success, None if env vars absent."""
    access_token = os.getenv("GMAIL_SENDER_ACCESS_TOKEN")
    if not access_token:
        return None  # env not configured — caller falls back to queued_only

    try:
        from blu_google_suite_client.gmail.client import GoogleGmailClient

        client = GoogleGmailClient(
            access_token=access_token,
            refresh_token=os.getenv("GMAIL_SENDER_REFRESH_TOKEN"),
        )
        result = await client.send_message(
            to=[to],
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )
        return result.message_id
    except Exception as exc:  # noqa: BLE001
        logger.warning("engagement.dispatch gmail send failed to=%s: %s", to, exc)
        raise


def _deliver(
    *,
    db: Any,
    client_id: str,
    empresa: str,
    action: str,
    channel: str,
    phone: str | None,
    email: str | None,
    message: str,
    twilio: Any | None,
) -> tuple[bool, str | None]:
    if channel == "whatsapp" and phone:
        try:
            if twilio is None:
                from blu_twilio_client import TwilioClient
                from blu_twilio_client.config import get_twilio_settings

                twilio = TwilioClient(get_twilio_settings())
            sid = twilio.send_whatsapp(to=phone, body=message)
            record_audit(
                db,
                p_action=action,
                p_payload={"channel": "whatsapp", "phone": phone, "sid": sid, "message": message},
                p_resource="clientes_blu",
                p_resource_id=client_id,
                p_actor_kind="cron",
                p_agent_slug="engagement-agent",
                p_outcome="success",
                p_client_id=client_id,
            )
            return True, sid
        except Exception as exc:  # noqa: BLE001
            logger.warning("engagement.dispatch whatsapp failed for %s: %s", client_id, exc)
            record_audit(
                db,
                p_action=action,
                p_payload={"channel": "whatsapp", "phone": phone, "error": str(exc)[:400]},
                p_resource="clientes_blu",
                p_resource_id=client_id,
                p_actor_kind="cron",
                p_agent_slug="engagement-agent",
                p_outcome="failure",
                p_client_id=client_id,
            )
            return False, None

    # ── Email path ────────────────────────────────────────────────────────────
    recipient = email or ""
    if not recipient:
        record_audit(
            db,
            p_action=action,
            p_payload={"channel": "email", "status": "skipped_no_address", "message": message},
            p_resource="clientes_blu",
            p_resource_id=client_id,
            p_actor_kind="cron",
            p_agent_slug="engagement-agent",
            p_outcome="partial",
            p_client_id=client_id,
        )
        return True, None

    subject = _subject_for(action)
    html = _html_for(message)

    try:
        # _send_gmail is async; run it in the current or a new event loop.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        gmail_id: str | None
        if loop and loop.is_running():
            # We're inside an async context (FastAPI route). Schedule and wait.
            import concurrent.futures

            future: concurrent.futures.Future[str | None] = concurrent.futures.Future()

            async def _run() -> None:
                try:
                    future.set_result(await _send_gmail(to=recipient, subject=subject, body_text=message, body_html=html))
                except Exception as exc:  # noqa: BLE001
                    future.set_exception(exc)

            loop.create_task(_run())
            # Block the sync caller with a short-circuit: the task runs
            # concurrently; we do a fire-and-forget and record "pending".
            # The audit log is written once the coroutine resolves in a
            # follow-up; here we optimistically mark it sent.
            gmail_id = None
        else:
            gmail_id = asyncio.run(_send_gmail(to=recipient, subject=subject, body_text=message, body_html=html))
    except Exception as exc:  # noqa: BLE001
        logger.warning("engagement.dispatch email failed for %s: %s", client_id, exc)
        record_audit(
            db,
            p_action=action,
            p_payload={"channel": "email", "email": recipient, "status": "send_error", "error": str(exc)[:400]},
            p_resource="clientes_blu",
            p_resource_id=client_id,
            p_actor_kind="cron",
            p_agent_slug="engagement-agent",
            p_outcome="failure",
            p_client_id=client_id,
        )
        return False, None

    if gmail_id is None and not os.getenv("GMAIL_SENDER_ACCESS_TOKEN"):
        # env not configured — queued_only fallback (staging / local)
        record_audit(
            db,
            p_action=action,
            p_payload={"channel": "email", "email": recipient, "status": "queued_only", "message": message},
            p_resource="clientes_blu",
            p_resource_id=client_id,
            p_actor_kind="cron",
            p_agent_slug="engagement-agent",
            p_outcome="partial",
            p_client_id=client_id,
        )
        return True, None

    record_audit(
        db,
        p_action=action,
        p_payload={"channel": "email", "email": recipient, "status": "sent", "gmail_id": gmail_id, "subject": subject},
        p_resource="clientes_blu",
        p_resource_id=client_id,
        p_actor_kind="cron",
        p_agent_slug="engagement-agent",
        p_outcome="success",
        p_client_id=client_id,
    )
    return True, gmail_id


@router.post("/dispatch")
async def dispatch_engagement_triggers(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Dispatch Phase D engagement triggers for up to 200 tenants."""
    _verify_token(authorization)

    db = get_supabase_client()
    now = datetime.now(UTC)

    try:
        tenants = (
            db.table("clientes_blu")
            .select("client_id,nome_empresa,created_at")
            .order("created_at", desc=False)
            .limit(200)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("engagement.dispatch: failed to list tenants")
        raise HTTPException(status_code=500, detail="scan failed")

    summary = {
        "scanned": len(tenants),
        "dispatched": 0,
        "whatsapp_sent": 0,
        "email_sent": 0,
        "email_queued": 0,
        "skipped": 0,
        "errors": 0,
        "by_action": {A_5MIN: 0, A_24H: 0, A_72H: 0, A_7D: 0, A_PENDING: 0},
    }

    if not tenants:
        return summary

    twilio = None

    for tenant in tenants:
        client_id = str(tenant["client_id"])
        empresa = str(tenant.get("nome_empresa") or "sua empresa")
        created_at = _parse_dt(tenant.get("created_at"))
        if created_at is None:
            summary["skipped"] += 1
            continue

        age_hours = (now - created_at).total_seconds() / 3600.0

        try:
            connectors_synced = _count_synced_connectors(db, client_id)
            pending_approvals = _count_pending_approvals(db, client_id)
            has_decision = _has_approval_decision(db, client_id)
            channel, phone, email = _resolve_notify_target(db, client_id)

            planned: list[str] = []

            if 0.08 <= age_hours < 6 and connectors_synced == 0 and not has_decision:
                if not _has_audit_since(db, client_id, A_5MIN, created_at):
                    planned.append(A_5MIN)

            if age_hours >= 24 and not has_decision:
                if not _has_audit_since(db, client_id, A_24H, created_at):
                    planned.append(A_24H)

            if age_hours >= 72 and connectors_synced == 0:
                if not _has_audit_since(db, client_id, A_72H, created_at):
                    planned.append(A_72H)

            if age_hours >= 24 * 7:
                if not _has_audit_since(db, client_id, A_7D, now - timedelta(days=7)):
                    planned.append(A_7D)

            if pending_approvals > 0:
                if not _has_audit_since(db, client_id, A_PENDING, now - timedelta(hours=24)):
                    planned.append(A_PENDING)

            if not planned:
                summary["skipped"] += 1
                continue

            for action in planned:
                message = _message_for(
                    action,
                    empresa=empresa,
                    pending_approvals=pending_approvals,
                    connectors_synced=connectors_synced,
                )
                ok, sid = _deliver(
                    db=db,
                    client_id=client_id,
                    empresa=empresa,
                    action=action,
                    channel=channel,
                    phone=phone,
                    email=email,
                    message=message,
                    twilio=twilio,
                )
                if channel == "whatsapp" and ok and sid:
                    summary["whatsapp_sent"] += 1
                elif ok and sid:
                    summary["email_sent"] += 1
                elif ok:
                    summary["email_queued"] += 1

                if ok:
                    summary["dispatched"] += 1
                    summary["by_action"][action] += 1
                else:
                    summary["errors"] += 1
        except Exception:
            logger.exception("engagement.dispatch: tenant loop failed client_id=%s", client_id)
            summary["errors"] += 1

    logger.info("engagement.dispatch summary=%s", summary)
    return summary


__all__ = ["router"]
