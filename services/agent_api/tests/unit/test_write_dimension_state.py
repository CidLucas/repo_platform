"""
Unit tests for memory.write_dimension_state routine function.

Tests the new Room Monitor shared memory write function without hitting
a real Supabase instance — uses AsyncMock to intercept asyncio.to_thread calls.
"""

from __future__ import annotations

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _call_write(inputs: dict, client_id: str = "test-client-uuid") -> dict:
    """Import and call the registered function directly via the call() dispatcher."""
    from agent_api.core.routine_functions import call as call_function
    return await call_function("memory.write_dimension_state", inputs, client_id)


def _make_mock_db(upsert_data: list | None = None):
    """Return a mock Supabase client whose table().upsert().execute() chain works."""
    execute_resp = MagicMock()
    execute_resp.data = upsert_data or []

    execute_chain = MagicMock()
    execute_chain.execute.return_value = execute_resp

    upsert_chain = MagicMock()
    upsert_chain.upsert.return_value = execute_chain

    table_mock = MagicMock()
    table_mock.return_value = upsert_chain

    db = MagicMock()
    db.table = table_mock
    return db, upsert_chain


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestWriteDimensionStateHappyPath:
    """memory.write_dimension_state — success scenarios."""

    @pytest.mark.asyncio
    async def test_returns_memory_written_true(self):
        db, _ = _make_mock_db()
        with patch("agent_api.core.routine_functions.asyncio.to_thread", new=AsyncMock(return_value=None)), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            result = await _call_write({
                "dimension": "financeiro",
                "summary": "Saldo R$12k, sem alertas críticos.",
            })
        assert result["memory_written"] is True
        assert result["dimension_written"] == "financeiro"

    @pytest.mark.asyncio
    async def test_upsert_called_with_correct_dimension(self):
        db, upsert_chain = _make_mock_db()
        captured_row: dict = {}

        async def fake_to_thread(fn, *args, **kwargs):
            row = fn()  # call the lambda to capture args
            # upsert was already called by the lambda — grab from mock
            return None

        with patch("agent_api.core.routine_functions.asyncio.to_thread", side_effect=fake_to_thread), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            await _call_write({
                "dimension": "compras",
                "summary": "3 SKUs críticos.",
                "ttl_hours": 24,
            })

        # The table("dimension_state") must be called
        db.table.assert_called_with("dimension_state")

    @pytest.mark.asyncio
    async def test_valid_until_is_in_future(self):
        """valid_until must be at least `ttl_hours` from now."""
        captured: dict = {}

        db, upsert_chain = _make_mock_db()

        # Replace upsert with a function that captures the row and returns a mock chain
        execute_mock = MagicMock()
        execute_mock.execute.return_value = MagicMock()
        
        def capture_upsert(row, **kwargs):
            captured.update(row)
            return execute_mock

        upsert_chain.upsert = capture_upsert

        async def fake_to_thread(fn, *args, **kwargs):
            fn()
            return None

        with patch("agent_api.core.routine_functions.asyncio.to_thread", side_effect=fake_to_thread), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            await _call_write({
                "dimension": "clientes",
                "summary": "Pipeline saudável.",
                "ttl_hours": 48,
            })

        assert "valid_until" in captured
        valid_until = datetime.datetime.fromisoformat(captured["valid_until"])
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = valid_until - now
        assert delta.total_seconds() > 47 * 3600  # at least 47h ahead

    @pytest.mark.asyncio
    async def test_default_ttl_is_24h(self):
        captured: dict = {}

        async def fake_to_thread(fn, *args, **kwargs):
            fn()
            return None

        db, upsert_chain = _make_mock_db()

        def capture_upsert(row, **kwargs):
            captured.update(row)
            return MagicMock()

        upsert_chain.upsert = capture_upsert

        with patch("agent_api.core.routine_functions.asyncio.to_thread", side_effect=fake_to_thread), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            await _call_write({
                "dimension": "agenda",
                "summary": "Nenhum compromisso crítico.",
                # ttl_hours NOT provided — should default to 24
            })

        valid_until = datetime.datetime.fromisoformat(captured["valid_until"])
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = valid_until - now
        assert 23 * 3600 < delta.total_seconds() < 25 * 3600

    @pytest.mark.asyncio
    async def test_structured_data_is_passed(self):
        captured: dict = {}

        async def fake_to_thread(fn, *args, **kwargs):
            fn()
            return None

        db, upsert_chain = _make_mock_db()

        def capture_upsert(row, **kwargs):
            captured.update(row)
            return MagicMock()

        upsert_chain.upsert = capture_upsert

        structured = {"saldo_total": 12000, "total_debitos": 3000}
        with patch("agent_api.core.routine_functions.asyncio.to_thread", side_effect=fake_to_thread), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            await _call_write({
                "dimension": "financeiro",
                "summary": "Caixa saudável.",
                "structured": structured,
            })

        assert captured.get("structured") == structured

    @pytest.mark.asyncio
    async def test_all_valid_dimensions_accepted(self):
        dimensions = ["financeiro", "compras", "clientes", "agenda", "estrategia", "documentos"]
        for dim in dimensions:
            db, _ = _make_mock_db()
            with patch("agent_api.core.routine_functions.asyncio.to_thread", new=AsyncMock(return_value=None)), \
                 patch("blu_supabase_client.get_supabase_client", return_value=db):
                result = await _call_write({"dimension": dim, "summary": f"Estado de {dim}."})
            assert result["dimension_written"] == dim, f"failed for {dim}"


# ---------------------------------------------------------------------------
# Validation / error tests
# ---------------------------------------------------------------------------

class TestWriteDimensionStateValidation:
    """memory.write_dimension_state — input validation."""

    @pytest.mark.asyncio
    async def test_missing_dimension_raises(self):
        with pytest.raises(ValueError, match="dimension"):
            await _call_write({"summary": "Algum texto."})

    @pytest.mark.asyncio
    async def test_empty_dimension_raises(self):
        with pytest.raises(ValueError, match="dimension"):
            await _call_write({"dimension": "", "summary": "Texto."})

    @pytest.mark.asyncio
    async def test_missing_summary_raises(self):
        with pytest.raises(ValueError, match="summary"):
            await _call_write({"dimension": "financeiro"})

    @pytest.mark.asyncio
    async def test_empty_summary_raises(self):
        with pytest.raises(ValueError, match="summary"):
            await _call_write({"dimension": "financeiro", "summary": ""})

    @pytest.mark.asyncio
    async def test_none_structured_is_allowed(self):
        """structured=None is valid — should pass through."""
        db, _ = _make_mock_db()
        with patch("agent_api.core.routine_functions.asyncio.to_thread", new=AsyncMock(return_value=None)), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            result = await _call_write({
                "dimension": "compras",
                "summary": "OK.",
                "structured": None,
            })
        assert result["memory_written"] is True

    @pytest.mark.asyncio
    async def test_function_registered_under_correct_name(self):
        """memory.write_dimension_state must be discoverable via the dispatcher."""
        from agent_api.core.routine_functions import list_functions
        assert "memory.write_dimension_state" in list_functions()


# ---------------------------------------------------------------------------
# Integration smoke test (no real DB)
# ---------------------------------------------------------------------------

class TestWriteDimensionStateIntegration:
    """End-to-end call through the dispatcher (call()) with mocked DB."""

    @pytest.mark.asyncio
    async def test_full_dispatcher_path(self):
        db, _ = _make_mock_db()
        with patch("agent_api.core.routine_functions.asyncio.to_thread", new=AsyncMock(return_value=None)), \
             patch("blu_supabase_client.get_supabase_client", return_value=db):
            result = await _call_write(
                {
                    "dimension": "financeiro",
                    "summary": "Saldo R$15k, cobertura 22 dias, 2 faturas vencendo.",
                    "structured": {"saldo": 15000, "cobertura_dias": 22},
                    "ttl_hours": 12,
                },
                client_id="a1b2c3d4-0000-0000-0000-000000000001",
            )
        assert result == {"memory_written": True, "dimension_written": "financeiro"}
