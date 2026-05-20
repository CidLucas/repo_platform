"""Phase 3B — Consumer Inbox tests.

Covers:
  • twilio_inbound_routes resolution + consumer fallback in the webhook
  • draft_consumer_reply_core (LLM mocked)
  • send_consumer_reply_core policy gating (pending_approval vs sent)
  • tg_approval_apply_consumer_message trigger (DB integration)
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_TPA_SRC = Path(__file__).resolve().parent.parent / "services" / "tool_pool_api" / "src"
if str(_TPA_SRC) not in sys.path:
    sys.path.insert(0, str(_TPA_SRC))


# ---------------------------------------------------------------------------
# Mock helpers — minimal supabase-py-shaped chainable stub
# ---------------------------------------------------------------------------


class _Resp(SimpleNamespace):
    pass


class _Q:
    """Tiny chainable query mock that records calls and returns canned data."""

    def __init__(self, store: dict, table: str):
        self._store = store
        self._table = table
        self._filters: list[tuple[str, str, object]] = []
        self._select = "*"
        self._single = False
        self._update_payload: dict | None = None
        self._insert_payload: list[dict] | dict | None = None
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._delete = False

    def select(self, cols, *_a, **_kw):
        self._select = cols
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals)))
        return self

    def or_(self, _expr):
        # Loose: don't filter further. Tests assert end state, not query semantics.
        return self

    @property
    def not_(self):
        self._filters.append(("not_next", None, None))
        return self

    def is_(self, col, val):
        self._filters.append(("is", col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        self._single = True
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def delete(self):
        self._delete = True
        return self

    # -- terminal --

    def execute(self):
        rows = list(self._store.get(self._table, []))
        for op, col, val in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "in":
                rows = [r for r in rows if r.get(col) in val]
            elif op == "is":
                if val == "null" or val is None:
                    rows = [r for r in rows if r.get(col) is None]
            # not_next/loose ops: ignored
        if self._update_payload is not None:
            for r in rows:
                r.update(self._update_payload)
            return _Resp(data=rows)
        if self._delete:
            self._store[self._table] = [
                r for r in self._store.get(self._table, []) if r not in rows
            ]
            return _Resp(data=rows)
        if self._insert_payload is not None:
            payload = self._insert_payload
            payloads = payload if isinstance(payload, list) else [payload]
            inserted = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("created_at", datetime.now(UTC).isoformat())
                self._store.setdefault(self._table, []).append(row)
                inserted.append(row)
            return _Resp(data=inserted)
        if self._order:
            rows = sorted(
                rows, key=lambda r: r.get(self._order[0]) or "",
                reverse=self._order[1],
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._single:
            return _Resp(data=rows[0] if rows else None)
        return _Resp(data=rows)


class _DB:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}
        self.rpc_calls: list[tuple[str, dict]] = []

    def table(self, name):
        return _Q(self.store, name)

    def rpc(self, name, params=None):
        self.rpc_calls.append((name, params or {}))

        class _R:
            def execute(self_inner):
                return _Resp(data=None)

        return _R()


# ---------------------------------------------------------------------------
# Section 1 · webhook fallback — twilio_inbound_routes + consumer fallback
# ---------------------------------------------------------------------------


@pytest.fixture
def twilio_app(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from tool_pool_api.api.twilio_webhook_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestWebhookConsumerFallback:
    def test_unknown_supplier_with_route_creates_consumer_message(self, twilio_app, monkeypatch):
        db = _DB()
        client_id = str(uuid.uuid4())
        # The webhook resolves client_id from twilio_inbound_routes then
        # upserts contact + inbound message.
        db.store["twilio_inbound_routes"] = [
            {
                "twilio_number": "+14155551234",
                "client_id": client_id,
                "label": "test",
            }
        ]
        # No supplier matches the From number → fallback path engages.
        db.store["supplier_roster"] = []

        monkeypatch.setattr(
            "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
            lambda: db,
        )

        resp = twilio_app.post(
            "/webhooks/twilio/inbound",
            data={
                "From": "whatsapp:+5511988887777",
                "To": "whatsapp:+14155551234",
                "Body": "Olá, quero saber mais",
                "MessageSid": "SMxyz",
            },
        )
        assert resp.status_code == 200
        # contact created + message inserted
        assert len(db.store.get("consumer_contacts", [])) == 1
        contact = db.store["consumer_contacts"][0]
        assert contact["client_id"] == client_id
        assert contact["channel"] == "whatsapp"
        assert len(db.store.get("consumer_messages", [])) == 1
        msg = db.store["consumer_messages"][0]
        assert msg["direction"] == "inbound"
        assert msg["body"] == "Olá, quero saber mais"

    def test_unknown_supplier_without_route_is_silent(self, twilio_app, monkeypatch):
        db = _DB()
        db.store["twilio_inbound_routes"] = []
        db.store["supplier_roster"] = []

        monkeypatch.setattr(
            "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
            lambda: db,
        )

        resp = twilio_app.post(
            "/webhooks/twilio/inbound",
            data={
                "From": "whatsapp:+5511988887777",
                "To": "whatsapp:+14155557777",
                "Body": "oi",
                "MessageSid": "SMabc",
            },
        )
        assert resp.status_code == 200
        # no consumer_messages row inserted — webhook returned 200 silently
        assert db.store.get("consumer_messages", []) == []


# ---------------------------------------------------------------------------
# Section 2 · draft_consumer_reply_core — LLM mocked
# ---------------------------------------------------------------------------


class TestDraftConsumerReplyCore:
    @pytest.mark.asyncio
    async def test_draft_inserts_outbound_draft_row(self, monkeypatch):
        db = _DB()
        client_id = str(uuid.uuid4())
        contact_id = str(uuid.uuid4())
        db.store["consumer_contacts"] = [
            {
                "id": contact_id,
                "client_id": client_id,
                "channel": "whatsapp",
                "external_id": "+5511988887777",
                "display_name": "Cliente Teste",
            }
        ]
        db.store["consumer_messages"] = [
            {
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "contact_id": contact_id,
                "direction": "inbound",
                "status": "received",
                "body": "Quanto custa o pacote azul?",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]

        monkeypatch.setattr(
            "tool_pool_api.server.tool_modules.consumer_inbox_module.get_supabase_client",
            lambda: db,
        )

        # Mock the LLM
        fake_model = MagicMock()
        fake_model.ainvoke = AsyncMock(
            return_value=SimpleNamespace(content="Olá! O pacote azul custa R$ 199.")
        )
        with patch("blu_llm_service.get_model", return_value=fake_model):
            from tool_pool_api.server.tool_modules.consumer_inbox_module import (
                draft_consumer_reply_core,
            )

            result = await draft_consumer_reply_core(
                client_id=client_id, contact_id=contact_id
            )

        assert result["draft_text"].startswith("Olá!")
        assert result["channel"] == "whatsapp"
        drafts = [
            m for m in db.store["consumer_messages"]
            if m.get("status") == "draft"
        ]
        assert len(drafts) == 1
        assert drafts[0]["direction"] == "outbound"
        assert drafts[0]["client_id"] == client_id

    @pytest.mark.asyncio
    async def test_draft_rejects_unknown_contact(self, monkeypatch):
        from fastmcp.exceptions import ToolError

        db = _DB()
        monkeypatch.setattr(
            "tool_pool_api.server.tool_modules.consumer_inbox_module.get_supabase_client",
            lambda: db,
        )
        from tool_pool_api.server.tool_modules.consumer_inbox_module import (
            draft_consumer_reply_core,
        )
        with pytest.raises(ToolError):
            await draft_consumer_reply_core(
                client_id=str(uuid.uuid4()), contact_id=str(uuid.uuid4())
            )


# ---------------------------------------------------------------------------
# Section 3 · send_consumer_reply_core — policy gating
# ---------------------------------------------------------------------------


def _seed_draft(db, *, client_id, contact_id, channel="whatsapp"):
    msg_id = str(uuid.uuid4())
    db.store.setdefault("consumer_messages", []).append(
        {
            "id": msg_id,
            "client_id": client_id,
            "contact_id": contact_id,
            "channel": channel,
            "direction": "outbound",
            "status": "draft",
            "body": "Olá! Tudo bem?",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    return msg_id


class TestSendConsumerReplyCore:
    @pytest.mark.asyncio
    async def test_pending_approval_when_policy_requires(self, monkeypatch):
        db = _DB()
        client_id = str(uuid.uuid4())
        contact_id = str(uuid.uuid4())
        db.store["consumer_contacts"] = [
            {
                "id": contact_id,
                "client_id": client_id,
                "channel": "whatsapp",
                "external_id": "+5511988887777",
                "display_name": None,
            }
        ]
        msg_id = _seed_draft(db, client_id=client_id, contact_id=contact_id)

        monkeypatch.setattr(
            "tool_pool_api.server.tool_modules.consumer_inbox_module.get_supabase_client",
            lambda: db,
        )

        from blu_agent_framework.approval import PolicyDecision

        approval_row = {"id": str(uuid.uuid4()), "status": "pending"}

        def fake_request(self, **kwargs):
            return SimpleNamespace(id=approval_row["id"])

        with patch(
            "tool_pool_api.server.tool_modules.consumer_inbox_module.resolve_policy",
            return_value=PolicyDecision(
                requires_async_approval=True,
                mode="always",
                routed_role="comercial-responsible",
                sla_hours=24,
                threshold=None,
                reason="BASIC tier always-approval",
            ),
        ), patch(
            "blu_agent_framework.approval.ApprovalEngine.request",
            new=fake_request,
        ):
            from tool_pool_api.server.tool_modules.consumer_inbox_module import (
                send_consumer_reply_core,
            )

            result = await send_consumer_reply_core(
                client_id=client_id, message_id=msg_id
            )

        assert result["status"] == "pending_approval"
        msg = next(m for m in db.store["consumer_messages"] if m["id"] == msg_id)
        assert msg["status"] == "pending_approval"

    @pytest.mark.asyncio
    async def test_direct_send_when_policy_allows(self, monkeypatch):
        db = _DB()
        client_id = str(uuid.uuid4())
        contact_id = str(uuid.uuid4())
        db.store["consumer_contacts"] = [
            {
                "id": contact_id,
                "client_id": client_id,
                "channel": "whatsapp",
                "external_id": "+5511988887777",
                "display_name": None,
            }
        ]
        msg_id = _seed_draft(db, client_id=client_id, contact_id=contact_id)

        monkeypatch.setattr(
            "tool_pool_api.server.tool_modules.consumer_inbox_module.get_supabase_client",
            lambda: db,
        )

        from blu_agent_framework.approval import PolicyDecision

        fake_twilio = MagicMock()
        fake_twilio.send_whatsapp = MagicMock(return_value="SMsentSID")

        with patch(
            "tool_pool_api.server.tool_modules.consumer_inbox_module.resolve_policy",
            return_value=PolicyDecision(
                requires_async_approval=False,
                mode="never",
                routed_role=None,
                sla_hours=72,
                threshold=None,
                reason="ADMIN bypass",
            ),
        ), patch(
            "blu_twilio_client.TwilioClient", return_value=fake_twilio
        ), patch(
            "blu_twilio_client.config.get_twilio_settings",
            return_value=SimpleNamespace(
                account_sid="AC", auth_token="tok", whatsapp_from="whatsapp:+1"
            ),
        ):
            from tool_pool_api.server.tool_modules.consumer_inbox_module import (
                send_consumer_reply_core,
            )

            result = await send_consumer_reply_core(
                client_id=client_id, message_id=msg_id
            )

        assert result["status"] == "sent"
        assert result["external_id"] == "SMsentSID"
        msg = next(m for m in db.store["consumer_messages"] if m["id"] == msg_id)
        assert msg["status"] == "sent"
        assert msg["external_id"] == "SMsentSID"


# ---------------------------------------------------------------------------
# Section 4 · approval_apply_consumer_message trigger — DB integration
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db():
    from blu_supabase_client import get_supabase_client

    return get_supabase_client(use_service_role=True)


@pytest.fixture
def consumer_contact_row(db, client_id):
    cid = str(uuid.uuid4())
    db.table("consumer_contacts").insert(
        {
            "id": cid,
            "client_id": client_id,
            "channel": "whatsapp",
            "external_id": f"+5511{uuid.uuid4().int % 10**9:09d}",
            "display_name": "PH3B Test",
        }
    ).execute()
    yield cid
    db.table("consumer_messages").delete().eq("contact_id", cid).execute()
    db.table("consumer_contacts").delete().eq("id", cid).execute()


@pytest.fixture
def consumer_draft_row(db, client_id, consumer_contact_row):
    mid = str(uuid.uuid4())
    db.table("consumer_messages").insert(
        {
            "id": mid,
            "client_id": client_id,
            "contact_id": consumer_contact_row,
            "channel": "whatsapp",
            "direction": "outbound",
            "status": "pending_approval",
            "body": "PH3B trigger test",
        }
    ).execute()
    yield mid


@pytest.mark.integration
class TestApprovalApplyConsumerMessageTrigger:
    """tg_approval_apply_consumer_message — flips message status on decision."""

    def _insert_approval(self, db, *, client_id, message_id):
        approval_id = str(uuid.uuid4())
        db.table("approval_requests").insert(
            {
                "id": approval_id,
                "client_id": client_id,
                "agent_slug": "comercial-agent",
                "action": "send_consumer_reply",
                "payload": {"message_id": message_id},
                "status": "pending",
                "sla_hours": 72,
                "expires_at": (datetime.now(UTC) + timedelta(hours=72)).isoformat(),
            }
        ).execute()
        return approval_id

    def _decide(self, db, *, approval_id, decision, reason="phase3b-test"):
        db.table("approval_requests").update(
            {
                "status": decision,
                "decided_at": datetime.now(UTC).isoformat(),
                "decision_reason": reason,
            }
        ).eq("id", approval_id).execute()

    def _msg_status(self, db, message_id):
        resp = (
            db.table("consumer_messages")
            .select("status,failure_reason")
            .eq("id", message_id)
            .single()
            .execute()
        )
        return resp.data

    def test_approved_flips_message_to_approved(self, db, client_id, consumer_draft_row):
        approval_id = self._insert_approval(
            db, client_id=client_id, message_id=consumer_draft_row
        )
        try:
            self._decide(db, approval_id=approval_id, decision="approved")
            row = self._msg_status(db, consumer_draft_row)
            assert row["status"] == "approved"
        finally:
            db.table("approval_requests").delete().eq("id", approval_id).execute()

    def test_rejected_flips_message_to_failed(self, db, client_id, consumer_draft_row):
        approval_id = self._insert_approval(
            db, client_id=client_id, message_id=consumer_draft_row
        )
        try:
            self._decide(
                db, approval_id=approval_id, decision="rejected",
                reason="ph3b-rejected-test",
            )
            row = self._msg_status(db, consumer_draft_row)
            assert row["status"] == "failed"
            assert row["failure_reason"] == "ph3b-rejected-test"
        finally:
            db.table("approval_requests").delete().eq("id", approval_id).execute()
