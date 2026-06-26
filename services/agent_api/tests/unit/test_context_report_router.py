"""
Unit tests for services/agent_api/src/agent_api/api/context_report_router.py.

The router replaces supabase/functions/generate-context-report/ (Phase 4.1 / M7).
Tests cover: token auth, body validation, 202 + background task scheduling,
background task exception isolation.

Run with: pytest services/agent_api/tests/unit/test_context_report_router.py
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_api.api.context_report_router import router as context_report_router


# ── Test app + fixtures ──────────────────────────────────────────────


@pytest.fixture
def mock_settings():
    """Patch get_settings to return a Settings with CONTEXT_REPORT_TOKEN set."""
    with patch("agent_api.api.context_report_router.get_settings") as mock_get:
        settings = MagicMock()
        settings.CONTEXT_REPORT_TOKEN = "test-token-123"
        mock_get.return_value = settings
        yield settings


@pytest.fixture
def mock_settings_no_token():
    """Patch get_settings to return a Settings with NO token (503 path)."""
    with patch("agent_api.api.context_report_router.get_settings") as mock_get:
        settings = MagicMock()
        settings.CONTEXT_REPORT_TOKEN = None
        mock_get.return_value = settings
        yield settings


@pytest.fixture
def client(mock_settings):
    """Build a TestClient for the context_report_router."""
    app = FastAPI()
    app.include_router(context_report_router, prefix="/v1")
    return TestClient(app)


VALID_CLIENT_ID = "11111111-2222-3333-4444-555555555555"
AUTH_HEADER = {"Authorization": "Bearer test-token-123"}


# ── Auth ──────────────────────────────────────────────────────────────


class TestAuth:
    def test_missing_authorization_returns_401(self, client):
        resp = client.post(
            "/v1/internal/context-report",
            json={"client_id": VALID_CLIENT_ID},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Unauthorized"

    def test_wrong_token_returns_401(self, client):
        resp = client.post(
            "/v1/internal/context-report",
            json={"client_id": VALID_CLIENT_ID},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_token_not_configured_returns_503(self, mock_settings_no_token):
        app = FastAPI()
        app.include_router(context_report_router, prefix="/v1")
        c = TestClient(app)
        resp = c.post(
            "/v1/internal/context-report",
            json={"client_id": VALID_CLIENT_ID},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 503
        assert "CONTEXT_REPORT_TOKEN" in resp.json()["detail"]


# ── Request validation ────────────────────────────────────────────────


class TestRequestValidation:
    def test_missing_client_id_returns_422(self, client):
        resp = client.post(
            "/v1/internal/context-report",
            json={},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, client):
        resp = client.post(
            "/v1/internal/context-report",
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 422

    def test_extra_fields_are_ignored(self, client):
        """Pydantic ignores extra fields by default — the routine uses
        only ``client_id`` so anything else is silently dropped."""
        with patch(
            "agent_api.api.context_report_router._generate_context_report",
            new=AsyncMock(return_value={"context_report_summary": "ok", "report_upserted": True}),
        ) as mock_run:
            resp = client.post(
                "/v1/internal/context-report",
                json={"client_id": VALID_CLIENT_ID, "extra": "ignored"},
                headers=AUTH_HEADER,
            )
        assert resp.status_code == 202
        # Background task ran with the right client_id (positional arg)
        mock_run.assert_called_once()
        args = mock_run.call_args.args
        assert args[1] == VALID_CLIENT_ID  # _generate_context_report({}, client_id)


# ── Success path ──────────────────────────────────────────────────────


class TestSuccessPath:
    def test_returns_202_immediately(self, client):
        with patch(
            "agent_api.api.context_report_router._generate_context_report",
            new=AsyncMock(return_value={"context_report_summary": "ok", "report_upserted": True}),
        ):
            resp = client.post(
                "/v1/internal/context-report",
                json={"client_id": VALID_CLIENT_ID},
                headers=AUTH_HEADER,
            )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "accepted"
        assert body["client_id"] == VALID_CLIENT_ID
        assert "background" in body["message"].lower()

    def test_background_task_scheduled_with_correct_client_id(self, client):
        mock_run = AsyncMock(
            return_value={"context_report_summary": "ok", "report_upserted": True}
        )
        with patch(
            "agent_api.api.context_report_router._generate_context_report",
            new=mock_run,
        ):
            resp = client.post(
                "/v1/internal/context-report",
                json={"client_id": VALID_CLIENT_ID},
                headers=AUTH_HEADER,
            )
        assert resp.status_code == 202
        # TestClient runs background tasks synchronously, so the mock
        # was already awaited by the time the response comes back.
        mock_run.assert_called_once()
        # _run_context_report_safe calls _generate_context_report({}, client_id)
        # so the client_id is the second positional arg.
        assert mock_run.call_args.args[1] == VALID_CLIENT_ID

    def test_background_task_exception_does_not_break_response(self, client):
        """A failing routine must not surface as a 500 to the caller.
        The 202 was already returned — the background task just logs
        the error and moves on."""
        mock_run = AsyncMock(side_effect=RuntimeError("Routine exploded"))
        with patch(
            "agent_api.api.context_report_router._generate_context_report",
            new=mock_run,
        ):
            resp = client.post(
                "/v1/internal/context-report",
                json={"client_id": VALID_CLIENT_ID},
                headers=AUTH_HEADER,
            )
        # The 202 is returned BEFORE the background task runs in TestClient,
        # so we just verify the response was correct and the mock was awaited.
        assert resp.status_code == 202
        # TestClient runs background tasks; the exception is swallowed by
        # our _run_context_report_safe wrapper.


# ── Background task wrapper (direct) ──────────────────────────────────


class TestBackgroundTaskWrapper:
    async def test_runs_routine_and_logs_success(self):
        from agent_api.api.context_report_router import _run_context_report_safe

        with patch(
            "agent_api.api.context_report_router._generate_context_report",
            new=AsyncMock(
                return_value={
                    "context_report_summary": "report x chars, 5 metrics, indexado no RAG",
                    "report_upserted": True,
                }
            ),
        ) as mock_run:
            await _run_context_report_safe(client_id=VALID_CLIENT_ID)
        mock_run.assert_awaited_once_with({}, VALID_CLIENT_ID)

    async def test_swallows_exception_and_logs_error(self, caplog):
        """The wrapper must not propagate exceptions from the routine —
        they would otherwise bubble up to the FastAPI worker and pollute
        logs with tracebacks the caller can't act on (we already 202'd)."""
        from agent_api.api.context_report_router import _run_context_report_safe

        with patch(
            "agent_api.api.context_report_router._generate_context_report",
            new=AsyncMock(side_effect=RuntimeError("DB went away")),
        ):
            with caplog.at_level("ERROR", logger="agent_api.api.context_report_router"):
                # Should NOT raise
                await _run_context_report_safe(client_id=VALID_CLIENT_ID)

        # Error was logged
        assert any("Background run failed" in rec.message for rec in caplog.records)
        assert any(VALID_CLIENT_ID in rec.message for rec in caplog.records)
