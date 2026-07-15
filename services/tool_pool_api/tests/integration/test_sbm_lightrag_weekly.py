"""
Integration tests for sbm_to_lightrag_synthesis + sbm_lightrag_weekly
routine (T4.1g).

Tests the execute() function with mocked Supabase and LightRAG,
verifying end-to-end behavior: entity synthesis, KG summary write,
error resilience, and idempotency.

Note: get_supabase_client and get_context_service are imported lazily
inside execute() / _write_knowledge_graph_summary() via:
    from blu_supabase_client import get_supabase_client
    from tool_pool_api.server.dependencies import get_context_service

So we patch at their source modules, not on sbm_to_lightrag_synthesis.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from tool_pool_api.server.tool_modules.sbm_to_lightrag_synthesis import execute


# =============================================================================
# Helpers
# =============================================================================

CLIENT_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


def _make_sbm_row(
    entity_type: str,
    entity_name: str,
    key: str,
    value: dict | list | str | None = None,
    curated: bool = True,
) -> dict:
    """Build a single SBM row as returned by Supabase."""
    if value is None:
        value = {"sample": "data"}
    return {
        "id": str(uuid4()),
        "client_id": str(CLIENT_ID),
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": value,
        "metadata": {},
        "source": "test",
        "confidence": 0.9,
        "curated": curated,
        "expires_at": None,
        "created_at": "2026-06-15T10:00:00Z",
        "updated_at": "2026-06-15T10:00:00Z",
    }


def _build_mock_supabase(rows: list[dict]) -> MagicMock:
    """Build a mock Supabase client chain that returns the given rows."""
    mock_db = MagicMock()

    # Result of .execute()
    mock_result = MagicMock()
    mock_result.data = rows

    # The chain: all intermediate methods return self, .execute() returns result
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.order.return_value = chain
    chain.maybe_single.return_value = chain  # for fallback queries
    chain.execute = MagicMock(return_value=mock_result)

    # db.schema("public").table("shared_business_memory") → chain
    schema_mock = MagicMock()
    schema_mock.table.return_value = chain
    mock_db.schema.return_value = schema_mock

    return mock_db


def _build_mock_context_service(fail: bool = False) -> MagicMock:
    """Build a mock ContextService with Redis cache."""
    mock_ctx = MagicMock()
    mock_ctx.cache = MagicMock()
    if fail:
        mock_ctx.cache.set_json = MagicMock(
            side_effect=RuntimeError("Redis connection refused")
        )
    else:
        mock_ctx.cache.set_json = MagicMock()
    return mock_ctx


def _build_mock_rag_client(
    fail_for: set[str] | None = None,
    graph_stats: dict | None = None,
) -> MagicMock:
    """Build a mock LightRAG client with ainsert_custom_kg and get_graph_stats."""
    mock_rag = MagicMock()
    mock_rag.ainsert_custom_kg = AsyncMock()

    if fail_for:
        # Make ainsert_custom_kg fail for specific entity names
        async def _conditional_fail(**kwargs):
            entity_name = kwargs.get("entity_name", "")
            if entity_name in fail_for:
                raise RuntimeError(f"Simulated failure for {entity_name}")

        mock_rag.ainsert_custom_kg = AsyncMock(side_effect=_conditional_fail)

    if graph_stats is not None:
        mock_rag.get_graph_stats = AsyncMock(return_value=graph_stats)
    else:
        mock_rag.get_graph_stats = AsyncMock(return_value={
            "total_nodes": 10,
            "total_edges": 5,
            "top_by_degree": [
                {"name": "acme_corp", "degree": 5},
                {"name": "python_development", "degree": 3},
            ],
        })

    return mock_rag


# =============================================================================
# Integration: synthesis cycle
# =============================================================================

@pytest.mark.asyncio
async def test_synthesis_integration():
    """Populate SBM with 5+ curated entities, execute skill, verify KG inserts."""
    # Arrange: 6 entities across 5 types
    rows = [
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech"}),
        _make_sbm_row("client", "Acme Corp", "size", {"employees": 500}),
        _make_sbm_row("skill", "Python Development", "proficiency", "advanced"),
        _make_sbm_row("contact", "João Silva", "role", "CTO"),
        _make_sbm_row("supplier", "Fornecedor XYZ", "contract_status", "active"),
        _make_sbm_row("user", "Maria Souza", "department", "Engineering"),
        _make_sbm_row("snapshot", "Financeiro Semanal", "receita", {"valor": 50000}),
    ]

    mock_db = _build_mock_supabase(rows)
    mock_rag = _build_mock_rag_client()
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        result = await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    # Assert: all 6 entities processed
    assert result["processed"] == 6
    assert len(result["errors"]) == 0
    assert len(result["entities_synced"]) == 6

    # Verify ainsert_custom_kg was called 6 times
    assert mock_rag.ainsert_custom_kg.call_count == 6

    # Verify calls contain expected entity names
    called_names = [
        call.kwargs["entity_name"]
        for call in mock_rag.ainsert_custom_kg.call_args_list
    ]
    assert "acme_corp" in called_names
    assert "python_development" in called_names
    assert "contact:joao_silva" in called_names
    assert "fornecedor_xyz" in called_names
    assert "maria_souza" in called_names


@pytest.mark.asyncio
async def test_knowledge_graph_summary_updated():
    """After execute(), knowledge_graph_summary is written to Context Service."""
    rows = [
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech"}),
    ]

    mock_db = _build_mock_supabase(rows)
    mock_rag = _build_mock_rag_client(
        graph_stats={
            "top_by_degree": [{"name": "acme_corp", "degree": 10}],
        },
    )
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    # Verify set_json was called with correct key and data
    mock_ctx.cache.set_json.assert_called_once()
    call_args = mock_ctx.cache.set_json.call_args
    key = call_args[0][0]
    data = call_args[0][1]
    ttl = call_args[0][2]

    assert key == f"ctx:{CLIENT_ID}:knowledge_graph_summary"
    assert data["total_documents"] == 1
    assert data["total_entities"] == 1
    assert data["sync_status"] == "ok"
    assert len(data["top_entities_by_degree"]) == 1
    assert data["top_entities_by_degree"][0]["name"] == "acme_corp"
    assert ttl == 86400


@pytest.mark.asyncio
async def test_knowledge_graph_summary_redis_fallback():
    """When Context Service fails, KG summary falls back to SBM write."""
    rows = [
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech"}),
    ]

    mock_db = _build_mock_supabase(rows)

    # Get the existing chain (used by both SBM select and fallback upsert)
    schema_mock = mock_db.schema.return_value
    chain = schema_mock.table.return_value

    # Add upsert support to the chain for the fallback path
    mock_upsert_result = MagicMock()
    mock_upsert_result.data = [{"client_id": str(CLIENT_ID)}]

    mock_upsert_chain = MagicMock()
    mock_upsert_chain.on_conflict = MagicMock(return_value=mock_upsert_chain)
    mock_upsert_chain.execute = MagicMock(return_value=mock_upsert_result)

    chain.upsert.return_value = mock_upsert_chain

    mock_rag = _build_mock_rag_client()
    mock_ctx = _build_mock_context_service(fail=True)

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        result = await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    # Should still complete successfully
    assert result["processed"] == 1
    assert len(result["errors"]) == 0

    # Verify SBM fallback was called
    chain.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_error_resilience():
    """One entity with invalid data does not stop the cycle — others continue."""
    rows = [
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech"}),
        _make_sbm_row("skill", "Python Dev", "proficiency", "advanced"),
        _make_sbm_row("supplier", "Bad Supplier", "data", "will fail"),
        _make_sbm_row("user", "Maria Souza", "department", "Engineering"),
    ]

    mock_db = _build_mock_supabase(rows)

    # Make "Bad Supplier" → "bad_supplier" fail
    mock_rag = _build_mock_rag_client(fail_for={"bad_supplier"})
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        result = await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    # 3 entities should succeed, 1 should fail
    assert result["processed"] == 3
    assert len(result["errors"]) == 1
    assert result["errors"][0]["entity_name"] == "bad_supplier"
    assert result["errors"][0]["entity_type"] == "supplier"

    # All 4 entities still attempted (ainsert called 4 times)
    assert mock_rag.ainsert_custom_kg.call_count == 4

    # KG summary should still be written (with partial status)
    mock_ctx.cache.set_json.assert_called_once()
    data = mock_ctx.cache.set_json.call_args[0][1]
    assert data["sync_status"] == "partial"


@pytest.mark.asyncio
async def test_error_resilience_all_fail():
    """When ALL entities fail, sync_status is 'failed'."""
    rows = [
        _make_sbm_row("client", "Bad Corp", "data", "will fail"),
    ]

    mock_db = _build_mock_supabase(rows)
    mock_rag = _build_mock_rag_client(fail_for={"bad_corp"})
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        result = await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    assert result["processed"] == 0
    assert len(result["errors"]) == 1

    data = mock_ctx.cache.set_json.call_args[0][1]
    assert data["sync_status"] == "failed"


@pytest.mark.asyncio
async def test_idempotency():
    """Re-execution on same day uses same source_id (overwrite, not duplicate)."""
    rows = [
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech"}),
    ]

    mock_db = _build_mock_supabase(rows)
    mock_rag = _build_mock_rag_client()
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        # First execution
        result1 = await execute(client_id=CLIENT_ID, rag_client=mock_rag)
        assert result1["processed"] == 1

        # Second execution (same day → same source_id YYYYMMDD)
        result2 = await execute(client_id=CLIENT_ID, rag_client=mock_rag)
        assert result2["processed"] == 1

    # Both calls used the same source_id
    assert mock_rag.ainsert_custom_kg.call_count == 2

    source_ids = [
        call.kwargs["source_id"]
        for call in mock_rag.ainsert_custom_kg.call_args_list
    ]
    assert source_ids[0] == source_ids[1]  # same source_id → overwrite
    assert source_ids[0].startswith("sbm_synthesis_")  # YYYYMMDD format


@pytest.mark.asyncio
async def test_empty_sbm_returns_gracefully():
    """When SBM has no curated records, execute returns empty result without error."""
    mock_db = _build_mock_supabase([])
    mock_rag = _build_mock_rag_client()
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        result = await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    assert result["processed"] == 0
    assert len(result["errors"]) == 0
    assert result["entities_synced"] == []

    # No ainsert calls
    mock_rag.ainsert_custom_kg.assert_not_called()


@pytest.mark.asyncio
async def test_sbm_query_failure_propagates():
    """When SBM query fails, the error propagates as ToolError."""
    mock_db = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.order.return_value = chain
    chain.execute = MagicMock(side_effect=Exception("Connection refused"))
    schema_mock = MagicMock()
    schema_mock.table.return_value = chain
    mock_db.schema.return_value = schema_mock

    mock_rag = _build_mock_rag_client()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Failed to query shared_business_memory"):
            await execute(client_id=CLIENT_ID, rag_client=mock_rag)


@pytest.mark.asyncio
async def test_deduplication_by_key():
    """Records with same (entity_type, entity_name, key) are deduplicated —
    only the most recent (first by updated_at DESC) is kept."""
    rows = [
        # Most recent (first)
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech v2"}),
        # Duplicate key — should be skipped
        _make_sbm_row("client", "Acme Corp", "industry", {"sector": "Tech v1"}),
        # Unique key
        _make_sbm_row("client", "Acme Corp", "size", {"employees": 500}),
    ]

    mock_db = _build_mock_supabase(rows)
    mock_rag = _build_mock_rag_client()
    mock_ctx = _build_mock_context_service()

    with patch(
        "blu_supabase_client.get_supabase_client",
        new=MagicMock(return_value=mock_db),
    ), patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_ctx,
    ):
        result = await execute(client_id=CLIENT_ID, rag_client=mock_rag)

    assert result["processed"] == 1  # 1 entity, 2 unique keys → 1 synthesis

    # The synthesis markdown should contain the most recent value
    synthesis_call = mock_rag.ainsert_custom_kg.call_args
    description = synthesis_call.kwargs["description"]
    assert "Tech v2" in str(description)
    assert "500" in str(description) or "employees" in str(description)
