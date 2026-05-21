"""
Pluggy/Polp Open Finance webhook receiver — INF-04.

Pluggy POSTs events here when bank data changes for a connected item.
The router:

1. Validates the HMAC-SHA256 signature (X-Pluggy-Signature) when the
   shared secret is configured in the environment.
2. Resolves itemId → polp_integration_id → client_id.
3. Dispatches each event type:
   - item/updated         → upsert polp_integrations status
   - transaction/created  → upsert polp_transactions; fires 'new_transaction'
   - account/updated      → upsert polp_accounts; fires 'account_updated'
4. Calls fire_event_for_client via Supabase RPC so any subscribed routine
   (e.g. Alerta de Fluxo de Caixa) is automatically enqueued.

The endpoint is intentionally tolerant: unknown items or non-handled event
types return 200 immediately so Pluggy does not retry indefinitely.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response
from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/polp", tags=["Polp Webhooks"])

# ─── Signature validation ─────────────────────────────────────────────────────


def _validate_pluggy_signature(body: bytes, signature: str | None) -> bool:
    """Validate HMAC-SHA256 signature sent by Pluggy."""
    secret = os.getenv("PLUGGY_WEBHOOK_SECRET", "")
    if not secret:
        return True  # dev mode: skip validation
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    # Pluggy may send as "sha256=<hex>" or plain hex
    incoming = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, incoming)


# ─── DB helpers ───────────────────────────────────────────────────────────────


def _resolve_client_id(db: Any, item_id: int) -> str | None:
    """Map Pluggy itemId → client_id via polp_integrations."""
    try:
        resp = (
            db.table("polp_integrations")
            .select("client_id")
            .eq("polp_integration_id", item_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return str(rows[0]["client_id"]) if rows else None
    except Exception:
        logger.exception("polp_webhook: client_id lookup failed for itemId=%s", item_id)
        return None


def _upsert_account(db: Any, client_id: str, integration_id: str, acct: dict) -> None:
    """Upsert a Pluggy account into polp_accounts."""
    now_iso = datetime.now(UTC).isoformat()
    db.table("polp_accounts").upsert(
        {
            "client_id": client_id,
            "integration_id": integration_id,
            "polp_account_id": acct["id"],
            "type": acct.get("type", "BANK"),
            "subtype": acct.get("subtype"),
            "number": acct.get("number"),
            "name": acct.get("name"),
            "balance": float(acct.get("balance", 0)),
            "currency_code": acct.get("currencyCode", "BRL"),
            "marketing_name": acct.get("marketingName"),
            "owner": acct.get("owner"),
            "bank_data": acct.get("bankData"),
            "credit_data": acct.get("creditData"),
            "updated_at": now_iso,
        },
        on_conflict="client_id,polp_account_id",
    ).execute()


def _upsert_transaction(db: Any, client_id: str, tx: dict) -> None:
    """Upsert a Pluggy transaction into polp_transactions."""
    now_iso = datetime.now(UTC).isoformat()
    db.table("polp_transactions").upsert(
        {
            "client_id": client_id,
            "polp_account_id": tx.get("accountId"),
            "polp_transaction_id": tx["id"],
            "external_id": tx.get("externalId"),
            "description": tx.get("description"),
            "amount": float(tx.get("amount", 0)),
            "currency_code": tx.get("currencyCode", "BRL"),
            "date": tx.get("date"),
            "type": tx.get("type", "DEBIT"),
            "status": tx.get("status"),
            "balance_after": tx.get("balance"),
            "category": tx.get("category"),
            "merchant": tx.get("merchant"),  # preserves logo_url JSONB
            "payment_data": tx.get("paymentData"),
            "credit_card_metadata": tx.get("creditCardMetadata"),
            "updated_at": now_iso,
        },
        on_conflict="client_id,polp_transaction_id",
    ).execute()


def _fire_event(db: Any, client_id: str, event_type: str, payload: dict) -> None:
    """Call fire_event_for_client RPC to enqueue subscribed routines."""
    try:
        db.rpc(
            "fire_event_for_client",
            {
                "p_event_type": event_type,
                "p_client_id": client_id,
                "p_trigger_data": payload,
            },
        ).execute()
        logger.info("polp_webhook: fired '%s' for client=%s", event_type, client_id)
    except Exception as exc:
        logger.warning(
            "polp_webhook: fire_event failed event=%s client=%s: %s",
            event_type, client_id, exc,
        )


# ─── Webhook endpoint ─────────────────────────────────────────────────────────


@router.post("", status_code=200)
async def polp_webhook(
    request: Request,
    x_pluggy_signature: str | None = Header(default=None, alias="X-Pluggy-Signature"),
) -> Response:
    """Pluggy webhook endpoint for Open Finance data events."""
    body = await request.body()

    if not _validate_pluggy_signature(body, x_pluggy_signature):
        logger.warning("polp_webhook: invalid signature — rejecting")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload: dict = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("polp_webhook: invalid JSON body")
        return Response(content='{"ok":false}', media_type="application/json", status_code=200)

    event: str = payload.get("event", "")
    data: dict = payload.get("data", {})
    item_id: int | None = data.get("itemId") or payload.get("itemId")

    if item_id is None:
        logger.info("polp_webhook: event=%s has no itemId — ignoring", event)
        return Response(content='{"ok":true}', media_type="application/json")

    db = get_supabase_client()
    client_id = _resolve_client_id(db, int(item_id))
    if not client_id:
        logger.info("polp_webhook: unknown itemId=%s — ignoring", item_id)
        return Response(content='{"ok":true}', media_type="application/json")

    # Resolve the integration row UUID for foreign key on polp_accounts
    integration_resp = (
        db.table("polp_integrations")
        .select("id")
        .eq("polp_integration_id", int(item_id))
        .limit(1)
        .execute()
    )
    integration_rows = getattr(integration_resp, "data", None) or []
    integration_uuid = integration_rows[0]["id"] if integration_rows else None

    if event in ("item/updated", "item/created"):
        # Update integration status
        now_iso = datetime.now(UTC).isoformat()
        db.table("polp_integrations").update({
            "status": data.get("status", "UPDATED"),
            "execution_status": data.get("executionStatus"),
            "updated_at": now_iso,
        }).eq("polp_integration_id", int(item_id)).execute()
        logger.info("polp_webhook: item/updated for itemId=%s client=%s", item_id, client_id)

    elif event == "transaction/created":
        transactions: list[dict] = data.get("transactions", [])
        if not transactions:
            # Single transaction payload
            tx = data.get("transaction") or data
            if tx.get("id"):
                transactions = [tx]

        for tx in transactions:
            try:
                _upsert_transaction(db, client_id, tx)
            except Exception as exc:
                logger.warning(
                    "polp_webhook: upsert failed for tx_id=%s: %s",
                    tx.get("id"), exc,
                )

        if transactions:
            _fire_event(
                db,
                client_id,
                "new_transaction",
                {
                    "item_id": item_id,
                    "count": len(transactions),
                    "transaction_ids": [t.get("id") for t in transactions],
                },
            )
        logger.info(
            "polp_webhook: transaction/created count=%d client=%s",
            len(transactions), client_id,
        )

    elif event == "account/updated":
        accounts: list[dict] = data.get("accounts", [])
        if not accounts:
            acct = data.get("account") or data
            if acct.get("id"):
                accounts = [acct]

        if integration_uuid:
            for acct in accounts:
                try:
                    _upsert_account(db, client_id, integration_uuid, acct)
                except Exception as exc:
                    logger.warning(
                        "polp_webhook: upsert failed for acct_id=%s: %s",
                        acct.get("id"), exc,
                    )

        if accounts:
            _fire_event(
                db,
                client_id,
                "account_updated",
                {"item_id": item_id, "account_ids": [a.get("id") for a in accounts]},
            )
        logger.info(
            "polp_webhook: account/updated count=%d client=%s",
            len(accounts), client_id,
        )

    else:
        logger.debug("polp_webhook: unhandled event='%s' for client=%s", event, client_id)

    return Response(content='{"ok":true}', media_type="application/json")


__all__ = ["router"]
