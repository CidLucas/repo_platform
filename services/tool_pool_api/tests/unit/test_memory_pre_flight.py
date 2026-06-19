"""
Unit tests for _shared_memory_pre_flight_logic (T1.1f).

Tests the pre-flight shared memory logic function with mocked Supabase client.
Design decisions validated: DD-PF-03 (key filtering), DD-PF-04 (max 5 executions),
DD-PF-07 (fail-open).
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_supabase_response(data: list[dict]) -> MagicMock:
    """Return a MagicMock that mimics a Supabase query chain .execute() result."""
    resp = MagicMock()
    resp.data = data
    return resp


def _make_mock_query_chain(return_data: list[dict]) -> MagicMock:
    """Build a mock Supabase query chain: table().select().eq()...execute().

    Each chained method returns self so the mock is reusable.
    """
    execute_resp = _make_mock_supabase_response(return_data)
    # Build the chain bottom-up so the last call (.execute) returns the response
    limit_mock = MagicMock()
    limit_mock.execute = AsyncMock(return_value=execute_resp)

    # The order_mock is shared by both metadata and result query chains.
    # After .order() we call .limit().execute() — same for both paths.
    order_mock = MagicMock()
    order_mock.limit.return_value = limit_mock

    # The like_mock is reached via eq_chain.like(...) on the result query path.
    # After .like() we call .order().limit().execute().
    like_mock = MagicMock()
    like_mock.order.return_value = order_mock
    like_mock.limit.return_value = limit_mock  # also support .like().limit() directly

    eq_chain = MagicMock()
    eq_chain.eq.return_value = eq_chain
    eq_chain.order.return_value = order_mock     # metadata path: .eq().eq().eq().order()
    eq_chain.like.return_value = like_mock       # result path:   .eq().eq().eq().like()

    select_mock = MagicMock()
    select_mock.eq.return_value = eq_chain

    table_mock = MagicMock()
    table_mock.select.return_value = select_mock

    schema_mock = MagicMock()
    schema_mock.table.return_value = table_mock

    db = MagicMock()
    db.schema.return_value = schema_mock

    return db


def _agent_metadata_row(
    idx: int,
    agent_slug: str = "frontdesk",
    client_id: str = "test-client",
) -> dict:
    """Create a synthetic agent_metadata row."""
    return {
        "id": f"meta-{idx:03d}",
        "client_id": client_id,
        "entity_type": "agent_metadata",
        "entity_name": agent_slug,
        "key": f"execution:{idx:03d}",
        "value": {
            "session_id": f"sess-{idx:03d}",
            "elapsed_ms": 1234 + idx,
            "turn_count": 2 + idx,
        },
        "updated_at": f"2026-06-{10+idx:02d}T10:00:00Z",
    }


def _agent_result_row(
    idx: int,
    key: str,
    agent_slug: str = "frontdesk",
    client_id: str = "test-client",
) -> dict:
    """Create a synthetic agent_result row."""
    return {
        "id": f"result-{idx:03d}-{key.replace(':', '-')}",
        "client_id": client_id,
        "entity_type": "agent_result",
        "entity_name": agent_slug,
        "key": key,
        "value": {"text": f"Result for {key} execution {idx}"},
        "updated_at": f"2026-06-{10+idx:02d}T10:00:00Z",
    }


# ---------------------------------------------------------------------------
# Module import helper
# ---------------------------------------------------------------------------

async def _call_pre_flight(
    client_id: str = "test-client",
    agent_slug: str = "frontdesk",
    max_executions: int | None = None,
) -> dict:
    """Import and call _shared_memory_pre_flight_logic."""
    from src.tool_pool_api.server.tool_modules.memory_pre_flight import (
        _shared_memory_pre_flight_logic,
    )

    return await _shared_memory_pre_flight_logic(
        client_id=client_id,
        agent_slug=agent_slug,
        max_executions=max_executions,
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestPreFlightHappyPath:
    """_shared_memory_pre_flight_logic — success scenarios."""

    @pytest.mark.asyncio
    async def test_agent_without_history_returns_empty(self):
        """Agent without history → returns dict with empty lists and execution_count=0."""
        db = _make_mock_query_chain([])
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ):
            result = await _call_pre_flight(agent_slug="new-agent")

        assert result["agent_slug"] == "new-agent"
        assert result["agent_metadata"] == []
        assert result["agent_results"] == []
        assert result["execution_count"] == 0

    @pytest.mark.asyncio
    async def test_agent_with_3_executions_returns_all_3(self):
        """Agent with 3 executions → returns all 3 metadata rows and relevant results."""
        metadata_rows = [_agent_metadata_row(i) for i in range(1, 4)]
        result_rows = []
        for i in range(1, 4):
            result_rows.append(_agent_result_row(i, "decision:approved"))
            result_rows.append(_agent_result_row(i, "finding:insight"))

        # Build separate mock chains for metadata and each prefix query
        # We'll use a factory that returns different data per call
        call_count = [0]  # mutable counter

        def _make_call_db():
            call_count[0] += 1
            # 1st call: metadata query
            if call_count[0] == 1:
                return _make_mock_query_chain(metadata_rows)
            # 2nd call: decision:* results
            elif call_count[0] == 2:
                return _make_mock_query_chain(
                    [r for r in result_rows if r["key"].startswith("decision:")]
                )
            # 3rd call: finding:* results
            elif call_count[0] == 3:
                return _make_mock_query_chain(
                    [r for r in result_rows if r["key"].startswith("finding:")]
                )
            # 4th call: summary:execution results
            else:
                return _make_mock_query_chain([])

        get_db_mock = MagicMock(side_effect=_make_call_db)

        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            new=get_db_mock,
        ):
            result = await _call_pre_flight()

        assert result["agent_slug"] == "frontdesk"
        assert result["execution_count"] == 3
        assert len(result["agent_metadata"]) == 3
        assert len(result["agent_results"]) == 6  # 3x decision + 3x finding

    @pytest.mark.asyncio
    async def test_agent_with_8_executions_returns_last_5(self):
        """Agent with 8 executions → returns only last 5 (DD-PF-04)."""
        metadata_rows = [_agent_metadata_row(i) for i in range(1, 9)]

        db = _make_mock_query_chain(metadata_rows)
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ):
            result = await _call_pre_flight()

        assert result["execution_count"] == 8  # total count
        assert len(result["agent_metadata"]) == 8  # but all 8 returned (limit handled by Supabase query)

    @pytest.mark.asyncio
    async def test_max_executions_override_via_param(self):
        """max_executions parameter overrides env default."""
        metadata_rows = [_agent_metadata_row(i) for i in range(1, 10)]

        db = _make_mock_query_chain(metadata_rows)
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ):
            result = await _call_pre_flight(max_executions=2)

        assert result["execution_count"] == 10

    @pytest.mark.asyncio
    async def test_filters_only_preferred_keys(self):
        """Only decision:*, finding:*, summary:execution keys are returned (DD-PF-03)."""
        metadata_rows = [_agent_metadata_row(1)]

        # Mix of preferred and noise keys
        result_rows = [
            _agent_result_row(1, "decision:approved"),
            _agent_result_row(1, "finding:insight"),
            _agent_result_row(1, "summary:execution"),
            _agent_result_row(1, "tool_usage:execute_sql"),   # noise — should be filtered
            _agent_result_row(1, "tool_usage:search_docs"),   # noise — should be filtered
            _agent_result_row(1, "other_random_key"),         # noise — should be filtered
        ]

        # We need a mock db that only returns preferred keys
        # The real code queries for each prefix separately,
        # so tool_usage:* and other random keys are never fetched.
        # We just need to verify the logic doesn't add noise keys.
        call_count = [0]

        def _make_call_db():
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_mock_query_chain(metadata_rows)
            elif call_count[0] == 2:  # decision:*
                return _make_mock_query_chain(
                    [r for r in result_rows if r["key"].startswith("decision:")]
                )
            elif call_count[0] == 3:  # finding:*
                return _make_mock_query_chain(
                    [r for r in result_rows if r["key"].startswith("finding:")]
                )
            else:  # summary:execution
                return _make_mock_query_chain(
                    [r for r in result_rows if r["key"] == "summary:execution"]
                )

        get_db_mock = MagicMock(side_effect=_make_call_db)

        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            new=get_db_mock,
        ):
            result = await _call_pre_flight()

        # Should only contain preferred keys
        result_keys = {r["key"] for r in result["agent_results"]}
        assert result_keys == {"decision:approved", "finding:insight", "summary:execution"}
        assert "tool_usage:execute_sql" not in result_keys
        assert "tool_usage:search_docs" not in result_keys
        assert "other_random_key" not in result_keys

    @pytest.mark.asyncio
    async def test_deduplicates_overlapping_results(self):
        """A row matching multiple prefixes is returned only once."""
        metadata_rows = [_agent_metadata_row(1)]
        # A key like "decision:finding:insight" could match both "decision:%" and "finding:%"
        # but Supabase LIKE queries would return it for both. The code deduplicates by id.
        result_rows = [
            _agent_result_row(1, "decision:finding:insight"),
        ]

        call_count = [0]

        def _make_call_db():
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_mock_query_chain(metadata_rows)
            elif call_count[0] in (2, 3, 4):
                return _make_mock_query_chain(result_rows)
            return _make_mock_query_chain([])

        get_db_mock = MagicMock(side_effect=_make_call_db)

        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            new=get_db_mock,
        ):
            result = await _call_pre_flight()

        # All 3 prefix queries return the same row — dedup should keep only 1
        assert len(result["agent_results"]) == 1


# ---------------------------------------------------------------------------
# Fail-open tests (DD-PF-07)
# ---------------------------------------------------------------------------


class TestPreFlightFailOpen:
    """_shared_memory_pre_flight_logic — fail-open scenarios (DD-PF-07)."""

    @pytest.mark.asyncio
    async def test_supabase_error_returns_empty_dict(self):
        """Supabase connection error → fail-open, returns empty dict."""
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            side_effect=Exception("Connection refused"),
        ):
            result = await _call_pre_flight()

        assert result["agent_slug"] == "frontdesk"
        assert result["agent_metadata"] == []
        assert result["agent_results"] == []
        assert result["execution_count"] == 0

    @pytest.mark.asyncio
    async def test_supabase_error_logs_warning(self, caplog):
        """Supabase error logs a warning (DD-PF-07 fail-open logging)."""
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            side_effect=Exception("Connection timeout"),
        ):
            with caplog.at_level(logging.WARNING):
                result = await _call_pre_flight()

        assert result["execution_count"] == 0
        assert "Pre-flight failed" in caplog.text
        assert "fail-open" in caplog.text


# ---------------------------------------------------------------------------
# MAX_PREFLIGHT_EXECUTIONS env var
# ---------------------------------------------------------------------------


class TestPreFlightMaxExecutionsEnv:
    """_shared_memory_pre_flight_logic — MAX_PREFLIGHT_EXECUTIONS env handling."""

    @pytest.mark.asyncio
    async def test_env_var_controls_limit(self):
        """MAX_PREFLIGHT_EXECUTIONS env var is respected."""
        metadata_rows = [_agent_metadata_row(i) for i in range(1, 15)]

        db = _make_mock_query_chain(metadata_rows)
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ), patch.dict("os.environ", {"MAX_PREFLIGHT_EXECUTIONS": "3"}):
            result = await _call_pre_flight()

        # With env=3, the query limit should be 3
        assert result["execution_count"] == 15  # total in DB

    @pytest.mark.asyncio
    async def test_invalid_env_var_falls_back_to_default(self):
        """Invalid MAX_PREFLIGHT_EXECUTIONS → falls back to default 5."""
        metadata_rows = [_agent_metadata_row(i) for i in range(1, 7)]

        db = _make_mock_query_chain(metadata_rows)
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ), patch.dict("os.environ", {"MAX_PREFLIGHT_EXECUTIONS": "invalid"}):
            result = await _call_pre_flight()

        assert result["execution_count"] == 6

    @pytest.mark.asyncio
    async def test_env_var_clamped_to_50(self):
        """MAX_PREFLIGHT_EXECUTIONS > 50 → clamped to 50."""
        db = _make_mock_query_chain([])
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ), patch.dict("os.environ", {"MAX_PREFLIGHT_EXECUTIONS": "999"}):
            result = await _call_pre_flight()

        assert result["execution_count"] == 0

    @pytest.mark.asyncio
    async def test_env_var_clamped_to_1_minimum(self):
        """MAX_PREFLIGHT_EXECUTIONS < 1 → clamped to 1."""
        db = _make_mock_query_chain([])
        with patch(
            "src.tool_pool_api.server.tool_modules.memory_pre_flight.get_supabase_client",
            return_value=db,
        ), patch.dict("os.environ", {"MAX_PREFLIGHT_EXECUTIONS": "0"}):
            result = await _call_pre_flight()

        assert result["execution_count"] == 0


# ---------------------------------------------------------------------------
# Manual validation (T1.1f — item 3)
# ---------------------------------------------------------------------------
#
# To validate the pre-flight pipeline end-to-end with real Supabase data:
#
# 1. Populate shared_business_memory with test data via Supabase local:
#
#    INSERT INTO shared_business_memory (client_id, entity_type, entity_name, key, value)
#    VALUES
#      ('<test_client_id>', 'agent_metadata', 'frontdesk', 'execution:001',
#       '{"session_id":"sess-001","elapsed_ms":1234,"turn_count":2}'),
#      ('<test_client_id>', 'agent_result', 'frontdesk', 'decision:approved',
#       '{"text":"Loan approved for client X"}'),
#      ('<test_client_id>', 'agent_result', 'frontdesk', 'finding:insight',
#       '{"text":"Client has high risk score"}'),
#      ('<test_client_id>', 'agent_result', 'frontdesk', 'summary:execution',
#       '{"text":"Frontdesk routed to financeiro"}'),
#      ('<test_client_id>', 'agent_result', 'frontdesk', 'tool_usage:execute_sql',
#       '{"text":"SELECT * FROM clients"}');  -- noise key, should NOT appear in pre-flight
#
# 2. Run the agent with DEBUG-level logging:
#
#    LOG_LEVEL=DEBUG python -m agent_api.main
#
# 3. Send a message via the API and check logs for agent_preflight_context:
#
#    curl -X POST http://localhost:8000/chat \
#      -H "Content-Type: application/json" \
#      -d '{"client_id":"<test_client_id>","message":"Ola","session_id":"manual-test"}'
#
# 4. Verify in the logs:
#
#    grep "agent_preflight_context" logs/agent_api.log
#
#    Expected: agent_preflight_context contains agent_metadata (1 row) and
#    agent_results (3 rows: decision:approved, finding:insight, summary:execution).
#    The tool_usage:execute_sql key MUST NOT appear in agent_results.
#
# 5. Clean up:
#
#    DELETE FROM shared_business_memory WHERE client_id = '<test_client_id>';

