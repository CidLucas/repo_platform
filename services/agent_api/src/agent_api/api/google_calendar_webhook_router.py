"""
Google Calendar push-notification webhook — INF-05.

Google POSTs to this endpoint when a watched calendar has changes.
The router:

1. POST /webhooks/google-calendar
   Validates X-Goog-Channel-Token against GOOGLE_CALENDAR_WEBHOOK_SECRET.
   Resolves X-Goog-Channel-ID → client_id via calendar_watch_channels.
   For resource_state = 'exists' (real change): fires 'calendar_changed' event.
   Sync and not_exists states are acknowledged but produce no event.

2. POST /webhooks/google-calendar/register
   Authenticated endpoint (service-role or internal) that calls the Google
   Calendar watch API and persists channel_id → client_id in
   calendar_watch_channels.  Called from the integration setup flow.

Depends on: INF-05 migration (calendar_watch_channels table).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel

from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/google-calendar", tags=["Google Calendar Webhooks"])


# ─── Signature helper ─────────────────────────────────────────────────────────


def _validate_channel_token(token: str | None) -> bool:
    """Validate X-Goog-Channel-Token against the configured secret."""
    secret = os.getenv("GOOGLE_CALENDAR_WEBHOOK_SECRET", "")
    if not secret:
        return True  # dev mode
    return bool(token) and token == secret


# ─── DB helpers ───────────────────────────────────────────────────────────────


def _resolve_client_id(channel_id: str) -> str | None:
    """Look up client_id for a registered watch channel."""
    db = get_supabase_client()
    try:
        resp = (
            db.table("calendar_watch_channels")
            .select("client_id")
            .eq("channel_id", channel_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return str(rows[0]["client_id"]) if rows else None
    except Exception:
        logger.exception("gcal_webhook: client_id lookup failed for channel=%s", channel_id)
        return None


def _fire_event(client_id: str, event_type: str, payload: dict) -> None:
    """Fire a domain event via fire_event_for_client RPC."""
    db = get_supabase_client()
    try:
        db.rpc(
            "fire_event_for_client",
            {
                "p_event_type": event_type,
                "p_client_id": client_id,
                "p_trigger_data": payload,
            },
        ).execute()
        logger.info("gcal_webhook: fired '%s' for client=%s", event_type, client_id)
    except Exception as exc:
        logger.warning(
            "gcal_webhook: fire_event failed event=%s client=%s: %s",
            event_type, client_id, exc,
        )


# ─── Push notification endpoint ───────────────────────────────────────────────


@router.post("")
async def google_calendar_push(
    request: Request,
    x_goog_channel_id: str | None = Header(default=None, alias="X-Goog-Channel-ID"),
    x_goog_channel_token: str | None = Header(default=None, alias="X-Goog-Channel-Token"),
    x_goog_resource_state: str | None = Header(default=None, alias="X-Goog-Resource-State"),
    x_goog_resource_id: str | None = Header(default=None, alias="X-Goog-Resource-ID"),
) -> Response:
    """
    Receive Google Calendar push notifications.
    Google expects a 200 response; errors should not return 4xx/5xx or Google
    will stop sending notifications.
    """
    if not _validate_channel_token(x_goog_channel_token):
        logger.warning("gcal_webhook: invalid channel token — rejecting channel=%s", x_goog_channel_id)
        # Return 200 to prevent Google from retrying (we just won't process it)
        return Response(status_code=200)

    resource_state = x_goog_resource_state or ""
    channel_id = x_goog_channel_id or ""

    # 'sync' is the initial handshake — acknowledge and return
    if resource_state == "sync":
        logger.info("gcal_webhook: sync handshake for channel=%s", channel_id)
        return Response(status_code=200)

    # 'exists' means a real change occurred; 'not_exists' means deletion
    if resource_state not in ("exists", "not_exists"):
        return Response(status_code=200)

    client_id = _resolve_client_id(channel_id)
    if not client_id:
        logger.info("gcal_webhook: unknown channel=%s — ignoring", channel_id)
        return Response(status_code=200)

    _fire_event(
        client_id,
        "calendar_changed",
        {
            "channel_id": channel_id,
            "resource_id": x_goog_resource_id,
            "resource_state": resource_state,
        },
    )
    return Response(status_code=200)


# ─── Watch registration endpoint ─────────────────────────────────────────────


class RegisterWatchRequest(BaseModel):
    client_id: str
    calendar_id: str = "primary"


@router.post("/register")
async def register_calendar_watch(body: RegisterWatchRequest) -> dict:
    """
    Register a Google Calendar watch channel for a client and persist the
    channel_id → client_id mapping in calendar_watch_channels.

    Called internally from the integration setup flow after Google OAuth
    credentials are confirmed.
    """
    from uuid import UUID

    from agent_api.core.factory import get_context_service
    from agent_api.core.routine_functions import _build_calendar_client  # noqa: PLC2701

    client_id = body.client_id
    cal_client = await _build_calendar_client(client_id)

    if not cal_client:
        raise HTTPException(
            status_code=422,
            detail="Google Calendar not connected for this client",
        )

    # Generate a stable channel ID and token
    channel_id = str(uuid.uuid4())
    channel_token = os.getenv("GOOGLE_CALENDAR_WEBHOOK_SECRET", channel_id)

    # Webhook URL: derived from AGENT_API_PUBLIC_URL env var
    base_url = os.getenv("AGENT_API_PUBLIC_URL", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=500, detail="AGENT_API_PUBLIC_URL not configured")

    webhook_url = f"{base_url}/webhooks/google-calendar"
    expiration = int((datetime.now(UTC) + timedelta(days=7)).timestamp() * 1000)

    try:
        watch_resp = await cal_client.watch_events(
            calendar_id=body.calendar_id,
            channel_id=channel_id,
            webhook_url=webhook_url,
            token=channel_token,
            expiration_ms=expiration,
        )
    except Exception as exc:
        logger.exception("gcal_webhook: watch registration failed for client=%s", client_id)
        raise HTTPException(status_code=502, detail=f"Google API error: {exc}") from exc

    # Persist channel_id → client_id
    db = get_supabase_client()
    db.table("calendar_watch_channels").upsert(
        {
            "channel_id": channel_id,
            "client_id": client_id,
            "calendar_id": body.calendar_id,
            "resource_id": watch_resp.get("resourceId"),
            "expires_at": datetime.fromtimestamp(expiration / 1000, tz=UTC).isoformat(),
        },
        on_conflict="client_id,calendar_id",
    ).execute()

    logger.info(
        "gcal_webhook: registered watch channel=%s for client=%s cal=%s",
        channel_id, client_id, body.calendar_id,
    )
    return {
        "channel_id": channel_id,
        "resource_id": watch_resp.get("resourceId"),
        "expires_at": datetime.fromtimestamp(expiration / 1000, tz=UTC).isoformat(),
    }


__all__ = ["router"]
