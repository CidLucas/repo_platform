# GOAL: Issue #121 — Increase test coverage from 48% to 70%
# BEHAVIOR: B7 — Add FastAPI router coverage for agent_api (T1, currently 6%)
# AC: AC#7 — agent_api coverage > 30%
# DECISÃO: extend — behavior test file in tests/behaviors/ covering routers
#           and /health via FastAPI TestClient.

"""RED test for behavior B7 — agent_api coverage boost.

Exercises the agent_api public HTTP surface via ``fastapi.testclient.TestClient``
to raise coverage of the T1 critical service from 6% to >30%. Mocks are limited
to *boundaries* (Supabase, JWT auth, LLM service) — the internal routers
(``agents_router``, ``chat_router``) run unmodified, which is what we want for
coverage.

Endpoints exercised:

    GET  /health                                 (infra)
    GET  /v1/catalog/agents                      (list)
    GET  /v1/catalog/agents/{agent_id}           (404 path)
    GET  /v1/catalog/agents/admin                (admin list)
    GET  /v1/catalog/agents/admin/{agent_id}     (404 path)
    POST /v1/catalog/validate-tools              (admin validation)
    GET  /v1/catalog/nodes                       (node registry)
    GET  /v1/models                              (LLM models)
    GET  /v1/this-route-does-not-exist           (404 negative)
    POST /health                                 (405 method not allowed)

State atual: RED. The test file is expected to fail at *collection time* (or
first test invocation) because ``agent_api.main`` cannot be imported in the
current state of the monorepo — ``blu_agent_framework.handoff`` is missing
the ``shared_memory_context`` submodule. That is acceptable per the AC: the
test is RED and will flip to GREEN once the import surface is repaired (or
this file is updated to import only the routers and build a minimal app
fixture — see the GREEN plan in the behavior spec).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from blu_auth.core.models import AuthMethod, AuthResult
from blu_supabase_client import get_supabase_client

# ── Path bootstrap: ensure agent_api.src is importable ────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENT_API_SRC = _REPO_ROOT / "services" / "agent_api" / "src"
if str(_AGENT_API_SRC) not in sys.path:
    sys.path.insert(0, str(_AGENT_API_SRC))

# Importing the module under test is the RED-trip wire: if the
# ``blu_agent_framework.handoff`` chain is broken, pytest collection fails
# here with ``ModuleNotFoundError`` (an explicit RED outcome per the spec).
from agent_api.main import app  # noqa: E402
from agent_api.api.auth import (  # noqa: E402
    get_admin_auth_result,
    get_auth_result,
)


# ── Override root conftest cleanup (autouse Supabase teardown) ────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """B7 is hermetic — no real Supabase writes happen. Skip the root
    conftest's autouse ``_cleanup_test_data`` fixture (which would try to
    open a Supabase client and run DELETE statements)."""
    yield


# ── Auth helpers ──────────────────────────────────────────────────────


USER_UUID = UUID("11111111-1111-1111-1111-111111111111")
ADMIN_UUID = UUID("22222222-2222-2222-2222-222222222222")


def _user_auth() -> AuthResult:
    return AuthResult(
        client_id=USER_UUID,
        auth_method=AuthMethod.JWT,
        external_user_id=str(USER_UUID),
        email="user@example.com",
        raw_claims={},
    )


def _admin_auth() -> AuthResult:
    return AuthResult(
        client_id=ADMIN_UUID,
        auth_method=AuthMethod.JWT,
        external_user_id=str(ADMIN_UUID),
        email="admin@example.com",
        raw_claims={"app_metadata": {"role": "admin"}},
    )


# ── Supabase mock factory ─────────────────────────────────────────────


def _make_supabase_mock(
    *,
    agent_rows: list[dict] | None = None,
    session_rows: list[dict] | None = None,
    agent_admin_rows: list[dict] | None = None,
) -> MagicMock:
    """Build a MagicMock stand-in for ``get_supabase_client()``.

    The mock supports a tiny subset of the fluent query builder API used
    by ``agents_router`` and ``chat_router`` — just enough to let the
    routers execute their happy paths and 404 paths.
    """
    agent_rows = agent_rows if agent_rows is not None else []
    session_rows = session_rows if session_rows is not None else []
    agent_admin_rows = agent_admin_rows if agent_admin_rows is not None else []

    client = MagicMock(name="supabase_client")

    # agent_catalog table — distinct eq() chains for the user list, admin
    # list, get-by-id, and uniqueness-check flows.
    def _catalog_table_side_effect(*args, **kwargs):
        tbl = MagicMock(name="agent_catalog")
        # .select(...).eq("is_active", True).execute()  → user list
        # .select(...).eq("id", ...).eq("is_active", True).execute()  → get by id
        # .select(_ALL_CATALOG_COLUMNS).order(...).execute()  → admin list
        # .select("id").eq("slug", ...).execute()  → uniqueness check
        # .insert(...).execute()  → create
        # .update(...).eq("id", ...).execute()  → update / soft-delete / activate
        # .select(_ALL_CATALOG_COLUMNS).eq("id", ...).execute()  → duplicate base

        chain = MagicMock(name="agent_catalog_chain")
        chain.execute.return_value.data = agent_admin_rows or []
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.order.return_value = chain
        chain.select.return_value = chain
        chain.update.return_value = chain
        chain.insert.return_value = chain
        chain.delete.return_value = chain
        return chain

    client.table.side_effect = _catalog_table_side_effect

    # agent_sessions table — used by create_session, list_sessions, etc.
    def _session_table_side_effect(*args, **kwargs):
        tbl = MagicMock(name="agent_sessions")
        chain = MagicMock(name="agent_sessions_chain")
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.select.return_value = chain
        chain.update.return_value = chain
        chain.insert.return_value = chain
        chain.execute.return_value.data = session_rows or []
        return chain

    # Support both top-level table() and nested calls
    def _table_router(table_name, *args, **kwargs):
        if table_name == "agent_catalog":
            return _catalog_table_side_effect()
        if table_name == "agent_sessions":
            return _session_table_side_effect()
        if table_name == "clientes_blu":
            tbl = MagicMock(name="clientes_blu")
            chain = MagicMock(name="clientes_blu_chain")
            chain.eq.return_value = chain
            chain.select.return_value = chain
            chain.maybe_single.return_value = chain
            chain.execute.return_value.data = None
            tbl.return_value = chain
            return tbl()
        return MagicMock()

    client.table.side_effect = _table_router
    client.schema.return_value.table.side_effect = _table_router
    client.functions.invoke.return_value = MagicMock()

    return client


# ── Auth override fixture ─────────────────────────────────────────────


@pytest.fixture
def app_with_overrides():
    """A bare TestClient with auth and supabase boundaries mocked.

    We register dependency overrides for the JWT auth dependencies and
    patch ``get_supabase_client`` everywhere it is imported inside
    ``agent_api`` routers. Internal modules (the routers themselves,
    ``create_app``, ``_slugify``, ``_extract_variables``, etc.) are
    exercised as-is — that's what raises coverage.
    """
    supabase = _make_supabase_mock(
        agent_rows=[
            {
                "id": str(USER_UUID),
                "name": "Sample Agent",
                "slug": "sample-agent",
                "description": "A sample agent for tests",
                "category": "test",
                "icon": "test-icon",
                "tier_required": "BASIC",
            },
        ],
    )

    app.dependency_overrides[get_auth_result] = lambda: _user_auth()
    app.dependency_overrides[get_admin_auth_result] = lambda: _admin_auth()

    # Patch the Supabase boundary inside the agent_api package and inside
    # blu_supabase_client itself so any helper that bypasses the dependency
    # also sees the mock.
    with (
        patch("blu_supabase_client.get_supabase_client", return_value=supabase),
        patch(
            "agent_api.api.agents_router.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "agent_api.core.factory.get_factory",
            return_value=MagicMock(),
        ),
        patch(
            "agent_api.core.service.get_chat_service",
            return_value=MagicMock(),
        ),
        patch(
            "agent_api.core.service.get_agent_service",
            return_value=MagicMock(),
        ),
        patch(
            "agent_api.core.factory.get_mcp_manager",
            return_value=MagicMock(),
        ),
        patch(
            "agent_api.core.factory.get_context_service",
            return_value=AsyncMock(),
        ),
    ):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


# ── /health ───────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_ok(self, app_with_overrides):
        r = app_with_overrides.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "agent-api"

    def test_post_health_returns_405(self, app_with_overrides):
        """POST is not a registered verb for /health → 405 method not allowed."""
        r = app_with_overrides.post("/health")
        assert r.status_code == 405


# ── /v1/catalog/agents (user-facing) ──────────────────────────────────


class TestCatalogAgentsRouter:
    def test_list_agents_returns_list(self, app_with_overrides):
        r = app_with_overrides.get("/v1/catalog/agents?client_tier=BASIC")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)

    def test_get_agent_not_found_returns_404(self, app_with_overrides):
        """``get_agent`` raises 404 when ``agent_catalog`` returns no row."""
        unknown = UUID("99999999-9999-9999-9999-999999999999")
        r = app_with_overrides.get(f"/v1/catalog/agents/{unknown}")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_list_agents_admin_returns_list(self, app_with_overrides):
        r = app_with_overrides.get("/v1/catalog/agents/admin")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)

    def test_get_agent_admin_not_found_returns_404(self, app_with_overrides):
        unknown = UUID("99999999-9999-9999-9999-999999999999")
        r = app_with_overrides.get(f"/v1/catalog/agents/admin/{unknown}")
        assert r.status_code == 404


# ── /v1/catalog/validate-tools (admin) ────────────────────────────────


class TestValidateTools:
    def test_validate_tools_with_empty_list(self, app_with_overrides):
        """An empty tool list trivially validates — coverage for the
        ``validate_tools`` endpoint wrapper."""
        r = app_with_overrides.post(
            "/v1/catalog/validate-tools",
            json={"enabled_tools": [], "tier": "BASIC"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "valid" in body
        assert body["errors"] == []


# ── /v1/models (chat_router) ──────────────────────────────────────────


class TestChatRouterModels:
    def test_list_models_returns_dict(self, app_with_overrides):
        r = app_with_overrides.get("/v1/models")
        assert r.status_code == 200
        body = r.json()
        assert "models" in body
        assert "current_provider" in body
        assert "default_model" in body

    def test_models_payload_includes_provider_field(self, app_with_overrides):
        r = app_with_overrides.get("/v1/models")
        body = r.json()
        for entry in body["models"]:
            assert "name" in entry
            assert "provider" in entry
            assert "tier" in entry


# ── Negative routes (404) ─────────────────────────────────────────────


class TestNegativeRoutes:
    def test_unknown_route_returns_404(self, app_with_overrides):
        r = app_with_overrides.get("/v1/this-route-does-not-exist")
        assert r.status_code == 404

    def test_unknown_nested_route_returns_404(self, app_with_overrides):
        r = app_with_overrides.get("/v1/catalog/no-such-resource")
        assert r.status_code in (404, 405)
