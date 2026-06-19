# tests/unit/test_memory_meta.py
"""Unit tests for shared_business_memory_meta logic functions (T4.2e).

Tests the internal _logic helpers that back the MCP tools
shared_memory_meta_read and shared_memory_meta_list.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tool_pool_api.server.tool_modules.memory_module import (
    _shared_memory_meta_list_logic,
    _shared_memory_meta_read_logic,
)

TEST_CLIENT_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers — build Supabase mock chains
# ---------------------------------------------------------------------------


def _make_execute_mock(return_data):
    """Build a mock ``.execute()`` that returns ``return_data``."""
    mock_exec = AsyncMock()
    mock_exec.return_value = MagicMock(data=return_data)
    return mock_exec


def _make_maybe_single_execute_mock(return_data):
    """Build a mock ``.execute()`` where ``.data`` holds a single row or None."""
    mock_exec = AsyncMock()
    mock_exec.return_value = MagicMock(data=return_data)
    return mock_exec


def _chain_mock_single(result_row):
    """Build a Supabase query chain for maybe_single() → execute()."""
    chain = MagicMock()
    chain.schema.return_value = chain
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute = _make_maybe_single_execute_mock(result_row)
    return chain


def _chain_mock_group_by(rows):
    """Build a Supabase query chain for group_by() → execute()."""
    chain = MagicMock()
    chain.schema.return_value = chain
    chain.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.group_by.return_value = chain
    chain.execute = _make_execute_mock(rows)
    return chain


# ---------------------------------------------------------------------------
# shared_memory_meta_read_logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_meta_read_success():
    """Read a single meta entry — happy path."""
    row = {
        "id": "meta-001",
        "client_id": TEST_CLIENT_ID,
        "entity_type": "kg_summary",
        "entity_name": "cliente_x",
        "key": "resumo_executivo",
        "body": {"texto": "Resumo do cliente X."},
        "source": "system",
        "confidence": 0.95,
        "created_at": "2026-06-18T12:00:00Z",
        "updated_at": "2026-06-19T10:00:00Z",
    }

    mock_db = _chain_mock_single(row)

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_module.get_supabase_client",
        return_value=mock_db,
    ):
        result = await _shared_memory_meta_read_logic(
            client_id=TEST_CLIENT_ID,
            entity_type="kg_summary",
            entity_name="cliente_x",
            key="resumo_executivo",
        )

    assert result["id"] == "meta-001"
    assert result["entity_type"] == "kg_summary"
    assert result["entity_name"] == "cliente_x"
    assert result["key"] == "resumo_executivo"
    assert result["body"] == {"texto": "Resumo do cliente X."}
    assert result["source"] == "system"
    assert result["confidence"] == 0.95
    assert result["created_at"] == "2026-06-18T12:00:00Z"
    assert result["updated_at"] == "2026-06-19T10:00:00Z"

    # Verify the query chain was called correctly
    mock_db.table.assert_called_once_with("shared_business_memory_meta")
    mock_db.select.assert_called_once_with("*")


@pytest.mark.asyncio
async def test_meta_read_not_found_raises_valueerror():
    """Read a non-existent meta entry → ValueError."""
    mock_db = _chain_mock_single(None)  # maybe_single → None

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_module.get_supabase_client",
        return_value=mock_db,
    ):
        with pytest.raises(ValueError, match="Meta entry not found"):
            await _shared_memory_meta_read_logic(
                client_id=TEST_CLIENT_ID,
                entity_type="dedup_mapping",
                entity_name="fornecedor_y",
                key="mapeamento_inexistente",
            )


@pytest.mark.asyncio
async def test_meta_read_invalid_entity_type():
    """Invalid entity_type → ValueError raised by validator."""
    with pytest.raises(ValueError, match="Invalid entity_type"):
        await _shared_memory_meta_read_logic(
            client_id=TEST_CLIENT_ID,
            entity_type="invalid_type",
            entity_name="entidade_x",
            key="alguma_chave",
        )


# ---------------------------------------------------------------------------
# shared_memory_meta_list_logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_meta_list_unfiltered():
    """List all meta entries without filter."""
    rows = [
        {
            "entity_type": "kg_summary",
            "entity_name": "cliente_x",
            "count": 3,
            "last_updated": "2026-06-19T10:00:00Z",
        },
        {
            "entity_type": "synthesis_output",
            "entity_name": "cliente_x",
            "count": 2,
            "last_updated": "2026-06-19T09:00:00Z",
        },
        {
            "entity_type": "dedup_mapping",
            "entity_name": "fornecedor_y",
            "count": 1,
            "last_updated": "2026-06-18T08:00:00Z",
        },
    ]

    mock_db = _chain_mock_group_by(rows)

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_module.get_supabase_client",
        return_value=mock_db,
    ):
        result = await _shared_memory_meta_list_logic(
            client_id=TEST_CLIENT_ID,
            entity_type=None,
        )

    assert result["total_entities"] == 3
    assert result["client_id"] == TEST_CLIENT_ID
    assert result["entity_type_filter"] is None
    assert result["by_type"] == {
        "kg_summary": 1,
        "synthesis_output": 1,
        "dedup_mapping": 1,
    }

    entities = result["entities"]
    assert len(entities) == 3
    # Sorted by (entity_type, entity_name)
    assert entities[0]["entity_type"] == "dedup_mapping"
    assert entities[0]["key_count"] == 1
    assert entities[1]["entity_type"] == "kg_summary"
    assert entities[1]["key_count"] == 3
    assert entities[2]["entity_type"] == "synthesis_output"
    assert entities[2]["key_count"] == 2


@pytest.mark.asyncio
async def test_meta_list_filtered_by_type():
    """List meta entries filtered by entity_type."""
    rows = [
        {
            "entity_type": "synthesis_output",
            "entity_name": "cliente_x",
            "count": 2,
            "last_updated": "2026-06-19T09:00:00Z",
        },
        {
            "entity_type": "synthesis_output",
            "entity_name": "fornecedor_y",
            "count": 5,
            "last_updated": "2026-06-18T08:00:00Z",
        },
    ]

    mock_db = _chain_mock_group_by(rows)

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_module.get_supabase_client",
        return_value=mock_db,
    ):
        result = await _shared_memory_meta_list_logic(
            client_id=TEST_CLIENT_ID,
            entity_type="synthesis_output",
        )

    assert result["total_entities"] == 2
    assert result["entity_type_filter"] == "synthesis_output"
    assert result["by_type"] == {"synthesis_output": 2}


@pytest.mark.asyncio
async def test_meta_list_empty():
    """No meta entries → empty result with zero counts."""
    mock_db = _chain_mock_group_by([])

    with patch(
        "src.tool_pool_api.server.tool_modules.memory_module.get_supabase_client",
        return_value=mock_db,
    ):
        result = await _shared_memory_meta_list_logic(
            client_id=TEST_CLIENT_ID,
            entity_type=None,
        )

    assert result["total_entities"] == 0
    assert result["by_type"] == {}
    assert result["entities"] == []


@pytest.mark.asyncio
async def test_meta_list_invalid_entity_type():
    """Invalid entity_type filter → ValueError."""
    with pytest.raises(ValueError, match="Invalid entity_type"):
        await _shared_memory_meta_list_logic(
            client_id=TEST_CLIENT_ID,
            entity_type="invalid_type",
        )
