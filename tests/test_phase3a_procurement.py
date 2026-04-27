"""Phase 3A (P3.1, P3.2, P3.3) — procurement approval + Twilio webhook + follow-ups.

Covers:
- ``resolve_policy()`` matrix across tiers (BASIC/SME/PRO/PREMIUM/ENTERPRISE/ADMIN),
  modes (always/threshold/never), and per-action overrides.
- ``tg_approval_apply_purchase_order`` trigger — flips
  ``purchase_orders.status`` on Approval Engine decisions.
- Twilio inbound webhook ``/webhooks/twilio/inbound`` — supplier resolution,
  parse delegation, audit_log entries, signature validation toggle.
- RFQ follow-ups endpoint ``/internal/rfq/follow-ups/run`` — bearer auth,
  threshold gating, ``follow_up_count`` bump, dispatched / skipped counts.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Make the tool_pool_api source tree importable for the FastAPI router tests.
_TPA_SRC = Path(__file__).resolve().parent.parent / "services" / "tool_pool_api" / "src"
if str(_TPA_SRC) not in sys.path:
    sys.path.insert(0, str(_TPA_SRC))


# ---------------------------------------------------------------------------
# Section 1 · resolve_policy() — pure unit tests, no DB
# ---------------------------------------------------------------------------


class TestResolvePolicy:
    """resolve_policy() decides whether actions need an Approvals-Tray row."""

    def _resolve(self, **kwargs):
        from vizu_agent_framework.approval import resolve_policy

        return resolve_policy(
            client_id=kwargs.pop("client_id", "c-1"),
            agent_slug=kwargs.pop("agent_slug", "rfq-agent"),
            action=kwargs.pop("action", "create_purchase_order"),
            payload=kwargs.pop("payload", {}),
            policy=kwargs.pop("policy", {}),
            tier=kwargs.pop("tier", "BASIC"),
        )

    def test_basic_tier_no_routed_role_no_async_required(self):
        decision = self._resolve(tier="BASIC")
        assert decision.requires_async_approval is False
        assert decision.routed_role is None
        assert "owner-only" in decision.reason

    def test_admin_tier_never_skips_approval(self):
        decision = self._resolve(tier="ADMIN")
        assert decision.requires_async_approval is False
        assert decision.mode == "never"

    def test_pro_tier_threshold_below_no_async(self):
        decision = self._resolve(tier="PRO", payload={"total_amount": 1000})
        assert decision.requires_async_approval is False
        assert decision.threshold == 5000.0
        assert "<" in decision.reason

    def test_pro_tier_threshold_above_requires_async(self):
        decision = self._resolve(tier="PRO", payload={"total_amount": 9999})
        assert decision.requires_async_approval is True
        assert decision.routed_role == "finance-responsible"
        assert "≥" in decision.reason

    def test_pro_tier_threshold_at_boundary_requires_async(self):
        decision = self._resolve(tier="PRO", payload={"total_amount": 5000})
        assert decision.requires_async_approval is True

    def test_pro_tier_missing_amount_defaults_to_async(self):
        decision = self._resolve(tier="PRO", payload={})
        assert decision.requires_async_approval is True
        assert "missing" in decision.reason

    def test_sme_tier_uses_same_defaults_as_pro(self):
        decision = self._resolve(tier="SME", payload={"total_amount": 6000})
        assert decision.requires_async_approval is True
        assert decision.routed_role == "finance-responsible"

    def test_premium_tier_threshold_behavior(self):
        decision = self._resolve(tier="PREMIUM", payload={"total_amount": 100})
        assert decision.requires_async_approval is False

    def test_enterprise_tier_always_requires_async(self):
        decision = self._resolve(tier="ENTERPRISE", payload={"total_amount": 10})
        assert decision.requires_async_approval is True
        assert decision.mode == "always"
        assert decision.routed_role == "finance-responsible"

    def test_unknown_tier_falls_back_to_default(self):
        decision = self._resolve(tier="UNRECOGNIZED")
        # default fallback is mode=always, no routed_role → no async
        assert decision.mode == "always"
        assert decision.requires_async_approval is False

    def test_per_action_override_threshold_wins(self):
        decision = self._resolve(
            tier="PRO",
            policy={"create_purchase_order": {"mode": "threshold", "threshold": 100.0}},
            payload={"total_amount": 200},
        )
        assert decision.requires_async_approval is True
        assert decision.threshold == 100.0

    def test_per_action_override_never_wins(self):
        decision = self._resolve(
            tier="PRO",
            policy={"create_purchase_order": {"mode": "never"}},
            payload={"total_amount": 999_999},
        )
        assert decision.requires_async_approval is False
        assert decision.mode == "never"

    def test_threshold_without_value_treated_as_always(self):
        decision = self._resolve(
            tier="PRO",
            policy={"create_purchase_order": {"mode": "threshold", "threshold": None}},
            payload={"total_amount": 1},
        )
        assert decision.mode == "threshold"
        # routed_role is preserved from PRO defaults → async required
        assert decision.requires_async_approval is True

    def test_unknown_mode_defaults_to_async(self):
        decision = self._resolve(
            tier="BASIC",
            policy={"create_purchase_order": {"mode": "weird"}},
        )
        assert decision.requires_async_approval is True

    def test_amount_coercion_handles_strings_and_garbage(self):
        d1 = self._resolve(tier="PRO", payload={"total_amount": "9000"})
        assert d1.requires_async_approval is True
        d2 = self._resolve(tier="PRO", payload={"total_amount": "abc"})
        # garbage → missing → require approval
        assert d2.requires_async_approval is True


# ---------------------------------------------------------------------------
# Section 2 · approval_apply_purchase_order trigger — DB integration test
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db():
    from vizu_supabase_client import get_supabase_client

    return get_supabase_client(use_service_role=True)


@pytest.fixture
def supplier_row(db, client_id):
    """Insert a temporary supplier for trigger tests; clean up after."""
    sup_id = str(uuid.uuid4())
    db.table("supplier_roster").insert(
        {
            "id": sup_id,
            "client_id": client_id,
            "name": "TestSupplier-PH3A",
            "contact_phone": "+5511999990001",
            "is_active": True,
        }
    ).execute()
    yield {"id": sup_id, "client_id": client_id}
    db.table("supplier_roster").delete().eq("id", sup_id).execute()


@pytest.fixture
def po_row(db, client_id, supplier_row):
    """Insert a draft PO and clean up after."""
    po_id = str(uuid.uuid4())
    db.table("purchase_orders").insert(
        {
            "id": po_id,
            "client_id": client_id,
            "supplier_id": supplier_row["id"],
            "session_id": "phase3a-test-session",
            "status": "pending_approval",
            "items": [{"description": "Test", "qty": 1, "unit_price": 10}],
            "total_amount": 10,
        }
    ).execute()
    yield po_id
    db.table("purchase_orders").delete().eq("id", po_id).execute()


@pytest.mark.integration
class TestApprovalApplyPurchaseOrderTrigger:
    """tg_approval_apply_purchase_order — flips PO status on decision.

    The Approval Engine RPCs derive ``client_id`` from JWT
    ``get_my_client_id()``; service-role calls cannot use them. We exercise
    the trigger by writing directly to ``approval_requests`` as service
    role, then UPDATEing the status — which is exactly what the trigger is
    keyed off (``AFTER UPDATE WHEN OLD.status IS DISTINCT FROM NEW.status``).
    """

    def _insert_approval(self, db, *, client_id, action, payload):
        approval_id = str(uuid.uuid4())
        db.table("approval_requests").insert(
            {
                "id": approval_id,
                "client_id": client_id,
                "agent_slug": "rfq-agent",
                "action": action,
                "payload": payload,
                "status": "pending",
                "sla_hours": 72,
                "expires_at": (datetime.now(UTC) + timedelta(hours=72)).isoformat(),
            }
        ).execute()
        return approval_id

    def _decide(self, db, *, approval_id, decision):
        db.table("approval_requests").update(
            {
                "status": decision,
                "decided_at": datetime.now(UTC).isoformat(),
                "decision_reason": "phase3a-test",
            }
        ).eq("id", approval_id).execute()

    def _po_status(self, db, po_id):
        resp = db.table("purchase_orders").select("status").eq("id", po_id).single().execute()
        return resp.data["status"]

    def test_create_po_approved_flips_to_draft(self, db, client_id, po_row):
        approval_id = self._insert_approval(
            db, client_id=client_id,
            action="create_purchase_order", payload={"po_id": po_row},
        )
        try:
            self._decide(db, approval_id=approval_id, decision="approved")
            assert self._po_status(db, po_row) == "draft"
        finally:
            db.table("approval_requests").delete().eq("id", approval_id).execute()

    def test_create_po_rejected_flips_to_cancelled(self, db, client_id, po_row):
        approval_id = self._insert_approval(
            db, client_id=client_id,
            action="create_purchase_order", payload={"po_id": po_row},
        )
        try:
            self._decide(db, approval_id=approval_id, decision="rejected")
            assert self._po_status(db, po_row) == "cancelled"
        finally:
            db.table("approval_requests").delete().eq("id", approval_id).execute()

    def test_approve_po_approved_flips_to_approved(self, db, client_id, po_row):
        approval_id = self._insert_approval(
            db, client_id=client_id,
            action="approve_purchase_order", payload={"po_id": po_row},
        )
        try:
            self._decide(db, approval_id=approval_id, decision="approved")
            resp = (
                db.table("purchase_orders")
                .select("status,approved_at")
                .eq("id", po_row)
                .single()
                .execute()
            )
            assert resp.data["status"] == "approved"
            assert resp.data["approved_at"] is not None
        finally:
            db.table("approval_requests").delete().eq("id", approval_id).execute()

    def test_missing_po_id_in_payload_is_noop(self, db, client_id):
        """Approval with no payload.po_id must not blow up; trigger logs and returns."""
        approval_id = self._insert_approval(
            db, client_id=client_id,
            action="create_purchase_order", payload={},
        )
        try:
            # Should not raise.
            self._decide(db, approval_id=approval_id, decision="approved")
        finally:
            db.table("approval_requests").delete().eq("id", approval_id).execute()


# ---------------------------------------------------------------------------
# Section 3 · /webhooks/twilio/inbound — FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def twilio_app(monkeypatch):
    """A minimal FastAPI app mounting only the Twilio webhook router.

    Forces ``TWILIO_AUTH_TOKEN`` to empty so signature validation is
    skipped — individual tests can re-enable it via monkeypatch.setenv.
    """
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tool_pool_api.api.twilio_webhook_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class _FakeQuery:
    """Chainable Supabase query stub returning canned data."""

    def __init__(self, data):
        self._data = data

    # All the methods that get chained — they all just return self.
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def single(self, *a, **k): return self
    def maybe_single(self, *a, **k): return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _FakeDB:
    def __init__(self, *, supplier=None, rfq=None):
        self._supplier = supplier
        self._rfq = rfq
        self.audit_calls: list[dict] = []
        self.rpc_calls: list[tuple[str, dict]] = []

    def table(self, name):
        if name == "supplier_roster":
            return _FakeQuery([self._supplier] if self._supplier else [])
        if name == "rfq_requests":
            return _FakeQuery([self._rfq] if self._rfq else [])
        return _FakeQuery([])

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        if name == "record_audit":
            self.audit_calls.append(params)
        return _FakeQuery(None)


class TestTwilioInboundWebhook:
    """Twilio webhook resolves supplier, parses, writes audit, returns TwiML."""

    def test_unknown_supplier_returns_friendly_twiml(self, twilio_app):
        fake_db = _FakeDB(supplier=None)
        with patch(
            "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
            return_value=fake_db,
        ):
            resp = twilio_app.post(
                "/webhooks/twilio/inbound",
                data={"From": "whatsapp:+5511999998888", "Body": "Olá"},
            )
        assert resp.status_code == 200
        assert "<Response>" in resp.text
        # Phase 3B: when no supplier matches the From number, the webhook now
        # returns a friendly inbox-fallback TwiML rather than the procurement-
        # specific "not enrolled" message.
        assert "Mensagem recebida" in resp.text

    def test_supplier_with_no_open_rfq_records_audit(self, twilio_app):
        supplier = {
            "id": "sup-1",
            "client_id": "client-1",
            "name": "Forn1",
            "contact_phone": "+5511999990001",
            "is_active": True,
        }
        fake_db = _FakeDB(supplier=supplier, rfq=None)
        with patch(
            "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
            return_value=fake_db,
        ):
            resp = twilio_app.post(
                "/webhooks/twilio/inbound",
                data={"From": "whatsapp:+5511999990001", "Body": "Olá"},
            )
        assert resp.status_code == 200
        assert "não há cotação aberta" in resp.text
        actions = [c[0] for c in fake_db.rpc_calls]
        assert "record_audit" in actions
        # outcome of the no-open audit entry is "partial"
        assert any(
            c["p_action"] == "rfq.inbound_no_open" and c["p_outcome"] == "partial"
            for c in fake_db.audit_calls
        )

    def test_open_rfq_calls_parse_core_and_records_success(self, twilio_app):
        supplier = {
            "id": "sup-1",
            "client_id": "client-1",
            "name": "Forn1",
            "contact_phone": "+5511999990001",
            "is_active": True,
        }
        rfq = {
            "id": "rfq-1",
            "status": "sent",
            "sent_at": "2026-04-27T10:00:00Z",
            "deadline": "2026-04-28T10:00:00Z",
            "communication_channel": "whatsapp",
        }
        fake_db = _FakeDB(supplier=supplier, rfq=rfq)
        parse_mock = AsyncMock(return_value={"confidence": "high", "items_parsed": 3})

        with (
            patch(
                "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch(
                "tool_pool_api.api.twilio_webhook_router.parse_supplier_reply_core",
                parse_mock,
            ),
        ):
            resp = twilio_app.post(
                "/webhooks/twilio/inbound",
                data={
                    "From": "whatsapp:+5511999990001",
                    "Body": "Item 1: R$10",
                    "MessageSid": "SM123",
                },
            )

        assert resp.status_code == 200
        assert "processada (3 item" in resp.text
        parse_mock.assert_awaited_once()
        # success audit
        assert any(
            c["p_action"] == "rfq.supplier_reply_parsed" and c["p_outcome"] == "success"
            for c in fake_db.audit_calls
        )

    def test_parse_failure_returns_friendly_ack_and_audits_failure(self, twilio_app):
        from fastmcp.exceptions import ToolError

        supplier = {
            "id": "sup-1",
            "client_id": "client-1",
            "name": "Forn1",
            "contact_phone": "+5511999990001",
            "is_active": True,
        }
        rfq = {
            "id": "rfq-1",
            "status": "sent",
            "sent_at": "2026-04-27T10:00:00Z",
            "deadline": "2026-04-28T10:00:00Z",
            "communication_channel": "whatsapp",
        }
        fake_db = _FakeDB(supplier=supplier, rfq=rfq)
        parse_mock = AsyncMock(side_effect=ToolError("LLM exploded"))

        with (
            patch(
                "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch(
                "tool_pool_api.api.twilio_webhook_router.parse_supplier_reply_core",
                parse_mock,
            ),
        ):
            resp = twilio_app.post(
                "/webhooks/twilio/inbound",
                data={"From": "whatsapp:+5511999990001", "Body": "?"},
            )

        assert resp.status_code == 200
        assert "dificuldade" in resp.text
        assert any(
            c["p_action"] == "rfq.inbound_parse_failed" and c["p_outcome"] == "failure"
            for c in fake_db.audit_calls
        )

    def test_invalid_signature_drops_message(self, twilio_app, monkeypatch):
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret-xyz")
        fake_db = _FakeDB(supplier={"id": "x", "client_id": "y", "name": "z",
                                     "contact_phone": "+1", "is_active": True})
        with (
            patch(
                "tool_pool_api.api.twilio_webhook_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch(
                "tool_pool_api.api.twilio_webhook_router.validate_twilio_signature",
                return_value=False,
            ),
        ):
            resp = twilio_app.post(
                "/webhooks/twilio/inbound",
                data={"From": "whatsapp:+5511999990001", "Body": "ok"},
                headers={"X-Twilio-Signature": "bogus"},
            )
        # Empty TwiML response, no supplier lookup audit.
        assert resp.status_code == 200
        assert "<Response" in resp.text
        # no rpc_calls should have been made (we returned before DB work)
        assert fake_db.rpc_calls == []


# ---------------------------------------------------------------------------
# Section 4 · /internal/rfq/follow-ups/run — FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def follow_ups_app(monkeypatch):
    monkeypatch.delenv("RFQ_FOLLOW_UPS_TOKEN", raising=False)
    monkeypatch.delenv("DAILY_INSIGHTS_RUNNER_TOKEN", raising=False)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tool_pool_api.api.rfq_follow_ups_router import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class _FollowUpsDB:
    """Mock DB tracking update() calls and rpc audits."""

    def __init__(self, rows):
        self._rows = rows
        self.updates: list[dict] = []
        self.audits: list[dict] = []

    class _Tbl:
        def __init__(self, parent, rows):
            self.parent = parent
            self.rows = rows
            self._update_payload = None

        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def in_(self, *a, **k): return self
        def lt(self, *a, **k): return self
        def order(self, *a, **k): return self
        def limit(self, *a, **k): return self

        # `.not_.is_("col", "null")` — supabase-py exposes `not_` as a
        # property returning a builder; mirror that by returning self.
        @property
        def not_(self):
            return self

        def is_(self, *a, **k):
            return self

        def update(self, payload):
            self._update_payload = payload
            return self

        def execute(self):
            if self._update_payload is not None:
                self.parent.updates.append(self._update_payload)
                self._update_payload = None
                return SimpleNamespace(data=None)
            return SimpleNamespace(data=self.rows)

    def table(self, name):
        if name == "rfq_requests":
            return _FollowUpsDB._Tbl(self, self._rows)
        return _FollowUpsDB._Tbl(self, [])

    def rpc(self, name, params):
        if name == "record_audit":
            self.audits.append(params)
        return _FollowUpsDB._Tbl(self, None)


class TestRfqFollowUpsEndpoint:
    """POST /internal/rfq/follow-ups/run — bearer + dispatch logic."""

    def test_unauthorized_when_token_set_and_missing_header(self, follow_ups_app, monkeypatch):
        monkeypatch.setenv("RFQ_FOLLOW_UPS_TOKEN", "shh")
        resp = follow_ups_app.post("/internal/rfq/follow-ups/run")
        assert resp.status_code == 401

    def test_unauthorized_with_wrong_token(self, follow_ups_app, monkeypatch):
        monkeypatch.setenv("RFQ_FOLLOW_UPS_TOKEN", "shh")
        resp = follow_ups_app.post(
            "/internal/rfq/follow-ups/run",
            headers={"Authorization": "Bearer nope"},
        )
        assert resp.status_code == 401

    def test_no_due_rows_returns_zero_summary(self, follow_ups_app):
        fake_db = _FollowUpsDB([])
        with patch(
            "tool_pool_api.api.rfq_follow_ups_router.get_supabase_client",
            return_value=fake_db,
        ):
            resp = follow_ups_app.post("/internal/rfq/follow-ups/run")
        assert resp.status_code == 200
        body = resp.json()
        assert body["scanned"] == 0
        assert body["dispatched"] == 0

    def test_t12h_dispatch_bumps_follow_up_count(self, follow_ups_app):
        now = datetime.now(UTC)
        deadline = (now + timedelta(hours=8)).isoformat()  # within 12h tier
        rfq = {
            "id": "rfq-1",
            "client_id": "c-1",
            "supplier_id": "sup-1",
            "items": [{"description": "x"}],
            "deadline": deadline,
            "follow_up_count": 0,
            "communication_channel": "whatsapp",
            "status": "sent",
            "supplier_roster": {
                "name": "Forn",
                "contact_phone": "+5511999990001",
                "is_active": True,
            },
        }
        fake_db = _FollowUpsDB([rfq])
        twilio_mock = MagicMock()
        twilio_mock.send_whatsapp.return_value = "SMxx"

        with (
            patch(
                "tool_pool_api.api.rfq_follow_ups_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch("vizu_twilio_client.TwilioClient", return_value=twilio_mock),
            patch("vizu_twilio_client.config.get_twilio_settings", return_value=MagicMock()),
        ):
            resp = follow_ups_app.post("/internal/rfq/follow-ups/run")

        body = resp.json()
        assert body["dispatched"] == 1
        assert body["by_milestone"]["12h"] == 1
        assert fake_db.updates and fake_db.updates[0]["follow_up_count"] == 1
        twilio_mock.send_whatsapp.assert_called_once()
        assert any(
            a["p_action"] == "rfq.follow_up.12h" and a["p_outcome"] == "success"
            for a in fake_db.audits
        )

    def test_t2h_dispatch_after_step1(self, follow_ups_app):
        now = datetime.now(UTC)
        deadline = (now + timedelta(hours=1)).isoformat()  # within 2h tier
        rfq = {
            "id": "rfq-2",
            "client_id": "c-1",
            "supplier_id": "sup-1",
            "items": [{"description": "x"}],
            "deadline": deadline,
            "follow_up_count": 1,  # already received 12h reminder
            "communication_channel": "whatsapp",
            "status": "sent",
            "supplier_roster": {
                "name": "Forn",
                "contact_phone": "+5511999990001",
                "is_active": True,
            },
        }
        fake_db = _FollowUpsDB([rfq])
        twilio_mock = MagicMock()
        twilio_mock.send_whatsapp.return_value = "SMyy"

        with (
            patch(
                "tool_pool_api.api.rfq_follow_ups_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch("vizu_twilio_client.TwilioClient", return_value=twilio_mock),
            patch("vizu_twilio_client.config.get_twilio_settings", return_value=MagicMock()),
        ):
            resp = follow_ups_app.post("/internal/rfq/follow-ups/run")

        body = resp.json()
        assert body["dispatched"] == 1
        assert body["by_milestone"]["2h"] == 1
        assert fake_db.updates[0]["follow_up_count"] == 2

    def test_deadline_passed_is_skipped(self, follow_ups_app):
        now = datetime.now(UTC)
        deadline = (now - timedelta(hours=1)).isoformat()
        rfq = {
            "id": "rfq-3",
            "client_id": "c-1",
            "supplier_id": "sup-1",
            "items": [],
            "deadline": deadline,
            "follow_up_count": 0,
            "communication_channel": "whatsapp",
            "status": "sent",
            "supplier_roster": {
                "name": "Forn",
                "contact_phone": "+1",
                "is_active": True,
            },
        }
        fake_db = _FollowUpsDB([rfq])
        with (
            patch(
                "tool_pool_api.api.rfq_follow_ups_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch("vizu_twilio_client.TwilioClient", return_value=MagicMock()),
            patch("vizu_twilio_client.config.get_twilio_settings", return_value=MagicMock()),
        ):
            resp = follow_ups_app.post("/internal/rfq/follow-ups/run")
        body = resp.json()
        assert body["dispatched"] == 0
        assert body["skipped"] == 1
        assert fake_db.updates == []

    def test_inactive_supplier_skipped(self, follow_ups_app):
        now = datetime.now(UTC)
        deadline = (now + timedelta(hours=8)).isoformat()
        rfq = {
            "id": "rfq-4",
            "client_id": "c-1",
            "supplier_id": "sup-1",
            "items": [],
            "deadline": deadline,
            "follow_up_count": 0,
            "communication_channel": "whatsapp",
            "status": "sent",
            "supplier_roster": {
                "name": "Forn",
                "contact_phone": "+1",
                "is_active": False,
            },
        }
        fake_db = _FollowUpsDB([rfq])
        with (
            patch(
                "tool_pool_api.api.rfq_follow_ups_router.get_supabase_client",
                return_value=fake_db,
            ),
            patch("vizu_twilio_client.TwilioClient", return_value=MagicMock()),
            patch("vizu_twilio_client.config.get_twilio_settings", return_value=MagicMock()),
        ):
            resp = follow_ups_app.post("/internal/rfq/follow-ups/run")
        assert resp.json()["skipped"] == 1
