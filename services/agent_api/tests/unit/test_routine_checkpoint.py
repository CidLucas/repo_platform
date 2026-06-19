"""
Unit tests for routine checkpoint in shared_business_memory (Issue #21).

Tests the _checkpoint_to_shared_memory helper and its invocation points
without hitting a real Supabase instance.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_supabase_client():
    """Return a mock Supabase client whose rpc().execute() chain works."""
    execute_resp = MagicMock()
    execute_resp.data = []

    execute_chain = MagicMock()
    execute_chain.execute.return_value = execute_resp

    rpc_chain = MagicMock()
    rpc_chain.rpc.return_value = execute_chain

    client = MagicMock()
    client.rpc = rpc_chain
    return client


async def _call_checkpoint(
    client_id: str = "uuid-1",
    routine_id: str = "daily_insights",
    exec_id: str = "exec-uuid",
    step_number: int = 1,
    state: dict | None = None,
):
    """Import and call _checkpoint_to_shared_memory directly."""
    from agent_api.core.routines import _checkpoint_to_shared_memory

    if state is None:
        state = {"key": "value", "client_id": client_id, "routine_name": routine_id,
                 "exec_id": exec_id}

    await _checkpoint_to_shared_memory(
        client_id=client_id,
        routine_id=routine_id,
        exec_id=exec_id,
        step_number=step_number,
        state=state,
    )


# ---------------------------------------------------------------------------
# Test: RPC called with correct arguments (test 1)
# ---------------------------------------------------------------------------

class TestUpsertRpcCalledWithCorrectArgs:
    """_checkpoint_to_shared_memory passes all 5 parameters to the RPC."""

    @pytest.mark.asyncio
    async def test_rpc_called_with_all_params(self):
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            await _call_checkpoint(
                client_id="uuid-1",
                routine_id="daily_insights",
                exec_id="exec-uuid",
                step_number=1,
                state={"key": "value"},
            )

        client.rpc.assert_called_once_with(
            "upsert_routine_checkpoint",
            {
                "p_client_id": "uuid-1",
                "p_routine_id": "daily_insights",
                "p_exec_id": "exec-uuid",
                "p_step_number": 1,
                "p_state_value": {"key": "value"},
            },
        )

    @pytest.mark.asyncio
    async def test_rpc_called_with_different_step_number(self):
        """Verify step_number is passed correctly for later steps."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            await _call_checkpoint(step_number=3, state={"output": "step3"})

        call_args = client.rpc.call_args
        assert call_args[1]["p_step_number"] == 3
        assert call_args[1]["p_state_value"] == {"output": "step3"}


# ---------------------------------------------------------------------------
# Test: RPC failure does not interrupt (test 2)
# ---------------------------------------------------------------------------

class TestRpcFailureDoesNotInterrupt:
    """Failure in shared_business_memory checkpoint must NOT raise."""

    @pytest.mark.asyncio
    async def test_rpc_exception_is_caught(self):
        client = _make_mock_supabase_client()
        client.rpc.side_effect = RuntimeError("Supabase unavailable")

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            # Should NOT raise — function returns None on failure
            result = await _call_checkpoint()
            assert result is None

    @pytest.mark.asyncio
    async def test_rpc_failure_logs_warning(self, caplog):
        client = _make_mock_supabase_client()
        client.rpc.side_effect = RuntimeError("Supabase unavailable")

        with patch("agent_api.core.routines.get_supabase_client", return_value=client), \
             caplog.at_level(logging.WARNING):
            await _call_checkpoint(
                routine_id="test_routine",
                exec_id="exec-123",
                step_number=2,
            )

        assert "shared_business_memory checkpoint failed" in caplog.text
        assert "non-fatal" in caplog.text
        assert "test_routine" in caplog.text
        assert "exec-123" in caplog.text


# ---------------------------------------------------------------------------
# Test: State saved is post-step (test 3)
# ---------------------------------------------------------------------------

class TestStateSavedIsPostStep:
    """The state passed to the RPC contains the output of step N."""

    @pytest.mark.asyncio
    async def test_state_includes_step_outputs(self):
        client = _make_mock_supabase_client()
        state_after_step = {
            "client_id": "uuid-1",
            "routine_name": "daily_insights",
            "exec_id": "exec-uuid",
            "cash_balance": 15000,
            "bills_due": 3,
            "step_output": "processed ok",
        }

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            await _call_checkpoint(step_number=2, state=state_after_step)

        call_args = client.rpc.call_args
        passed_state = call_args[1]["p_state_value"]
        assert passed_state["cash_balance"] == 15000
        assert passed_state["bills_due"] == 3
        assert passed_state["step_output"] == "processed ok"

    @pytest.mark.asyncio
    async def test_state_does_not_contain_previous_step_only(self):
        """Ensure complete state (not just diff) is passed."""
        client = _make_mock_supabase_client()
        full_state = {
            "client_id": "uuid-1",
            "routine_name": "daily_insights",
            "exec_id": "exec-uuid",
            "step1_output": "done",
            "step2_output": "done",
            "step3_output": "done",
        }

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            await _call_checkpoint(step_number=3, state=full_state)

        call_args = client.rpc.call_args
        passed_state = call_args[1]["p_state_value"]
        # All outputs should be present (complete state, not diff)
        assert "step1_output" in passed_state
        assert "step2_output" in passed_state
        assert "step3_output" in passed_state


# ---------------------------------------------------------------------------
# Test: Key pattern correct (test 4)
# ---------------------------------------------------------------------------

class TestKeyPatternCorrect:
    """Keys generated by the RPC follow the documented pattern."""

    @pytest.mark.asyncio
    async def test_entity_type_is_routine(self):
        """DD-01: entity_type must be 'routine'."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            await _call_checkpoint()

        call_args = client.rpc.call_args
        # Verify RPC function name
        assert call_args[0][0] == "upsert_routine_checkpoint"

    @pytest.mark.asyncio
    async def test_step_number_passed_correctly(self):
        """DD-04: step_number is passed to generate key patterns."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client):
            await _call_checkpoint(exec_id="abc-123", step_number=5)

        call_args = client.rpc.call_args
        assert call_args[1]["p_exec_id"] == "abc-123"
        assert call_args[1]["p_step_number"] == 5


# ---------------------------------------------------------------------------
# Test: First checkpoint logs info (test 5)
# ---------------------------------------------------------------------------

class TestFirstCheckpointLogsInfo:
    """Logger.info appears when step_number == 1."""

    @pytest.mark.asyncio
    async def test_step_1_logs_info(self, caplog):
        """step_number=1 should trigger logger.info."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client), \
             caplog.at_level(logging.INFO):
            await _call_checkpoint(step_number=1)

        # At least one INFO-level log should mention checkpoint
        info_messages = [r.message for r in caplog.records if r.levelno >= logging.INFO]
        assert any("Routine checkpoint enabled" in msg for msg in info_messages), \
            f"No checkpoint info log found in: {info_messages}"

    @pytest.mark.asyncio
    async def test_step_1_includes_routine_exec_client(self, caplog):
        """The info log should include routine, exec, and client IDs."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client), \
             caplog.at_level(logging.INFO):
            await _call_checkpoint(
                routine_id="daily_insights",
                exec_id="exec-456",
                client_id="client-789",
                step_number=1,
            )

        info_messages = [r.message for r in caplog.records if r.levelno >= logging.INFO]
        checkpoint_msgs = [m for m in info_messages if "checkpoint" in m.lower()]
        assert checkpoint_msgs
        # The log in the exec_loop format includes routine, exec, client
        msg = checkpoint_msgs[0]
        assert "daily_insights" in msg
        assert "exec-456" in msg
        assert "client-789" in msg


# ---------------------------------------------------------------------------
# Test: Subsequent checkpoints have no info log (test 6)
# ---------------------------------------------------------------------------

class TestSubsequentCheckpointsNoInfoLog:
    """Logger.info should NOT fire for steps 2+ (batch checkpoint path)."""

    @pytest.mark.asyncio
    async def test_step_2_no_info_log(self, caplog):
        """step_number=2 should NOT trigger the 'checkpoint enabled' log."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client), \
             caplog.at_level(logging.INFO):
            await _call_checkpoint(step_number=2)

        info_messages = [r.message for r in caplog.records if r.levelno >= logging.INFO]
        # No "Routine checkpoint enabled" message for step 2+
        assert not any("Routine checkpoint enabled" in msg for msg in info_messages), \
            f"Unexpected checkpoint info for step 2: {info_messages}"

    @pytest.mark.asyncio
    async def test_step_3_no_info_log(self, caplog):
        """step_number=3 should also not log info."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client), \
             caplog.at_level(logging.INFO):
            await _call_checkpoint(step_number=3)

        info_messages = [r.message for r in caplog.records if r.levelno >= logging.INFO]
        assert not any("Routine checkpoint enabled" in msg for msg in info_messages)

    @pytest.mark.asyncio
    async def test_step_0_no_info_log(self, caplog):
        """step_number=0 (unknown step) should not log info."""
        client = _make_mock_supabase_client()

        with patch("agent_api.core.routines.get_supabase_client", return_value=client), \
             caplog.at_level(logging.INFO):
            await _call_checkpoint(step_number=0)

        info_messages = [r.message for r in caplog.records if r.levelno >= logging.INFO]
        assert not any("Routine checkpoint enabled" in msg for msg in info_messages)
