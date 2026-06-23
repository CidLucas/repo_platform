"""Tests for knowledge_graph_sync module — update_knowledge_graph_summary."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from tool_pool_api.server.tool_modules.knowledge_graph_sync import (
    _REQUIRED_KEYS,
    _validate_summary,
    update_knowledge_graph_summary,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client_id() -> UUID:
    return UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def valid_summary() -> dict:
    return {
        "total_documents": 150,
        "total_entities": 80,
        "top_entities": [
            {"name": "Acme", "type": "organization", "degree": 42},
        ],
        "last_sync": "2025-06-19T12:00:00Z",
        "version": 1,
    }


# =============================================================================
# _validate_summary tests
# =============================================================================


class TestValidateSummary:
    """Unit tests for _validate_summary — called internally before DB ops."""

    def test_valid_summary_passes(self, valid_summary):
        _validate_summary(valid_summary)  # no exception

    def test_summary_not_a_dict_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            _validate_summary("not a dict")

    def test_missing_required_keys_raises(self):
        with pytest.raises(ValueError, match="missing required keys"):
            _validate_summary({"total_documents": 5})

    @pytest.mark.parametrize("key", sorted(_REQUIRED_KEYS))
    def test_each_required_key_missing_raises(self, key, valid_summary):
        bad = {k: v for k, v in valid_summary.items() if k != key}
        with pytest.raises(ValueError, match="missing required keys"):
            _validate_summary(bad)

    def test_total_documents_negative_raises(self, valid_summary):
        valid_summary["total_documents"] = -1
        with pytest.raises(ValueError, match="total_documents"):
            _validate_summary(valid_summary)

    def test_total_documents_not_int_raises(self, valid_summary):
        valid_summary["total_documents"] = "150"
        with pytest.raises(ValueError, match="total_documents"):
            _validate_summary(valid_summary)

    def test_total_entities_negative_raises(self, valid_summary):
        valid_summary["total_entities"] = -5
        with pytest.raises(ValueError, match="total_entities"):
            _validate_summary(valid_summary)

    def test_total_entities_not_int_raises(self, valid_summary):
        valid_summary["total_entities"] = 3.5
        with pytest.raises(ValueError, match="total_entities"):
            _validate_summary(valid_summary)

    def test_top_entities_not_list_raises(self, valid_summary):
        valid_summary["top_entities"] = "not a list"
        with pytest.raises(ValueError, match="top_entities must be a list"):
            _validate_summary(valid_summary)

    def test_top_entities_item_not_dict_raises(self, valid_summary):
        valid_summary["top_entities"] = ["not a dict"]
        with pytest.raises(ValueError, match="top_entities\\[0\\] must be a dict"):
            _validate_summary(valid_summary)

    def test_top_entities_item_missing_fields_raises(self, valid_summary):
        valid_summary["top_entities"] = [{"name": "Acme"}]
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_summary(valid_summary)

    def test_last_sync_wrong_type_raises(self, valid_summary):
        valid_summary["last_sync"] = 123
        with pytest.raises(ValueError, match="last_sync"):
            _validate_summary(valid_summary)

    def test_last_sync_none_is_ok(self, valid_summary):
        valid_summary["last_sync"] = None
        _validate_summary(valid_summary)  # no exception

    def test_version_not_int_raises(self, valid_summary):
        valid_summary["version"] = "1"
        with pytest.raises(ValueError, match="version"):
            _validate_summary(valid_summary)

    def test_version_zero_raises(self, valid_summary):
        valid_summary["version"] = 0
        with pytest.raises(ValueError, match="version"):
            _validate_summary(valid_summary)

    def test_version_negative_raises(self, valid_summary):
        valid_summary["version"] = -3
        with pytest.raises(ValueError, match="version"):
            _validate_summary(valid_summary)


# =============================================================================
# _REQUIRED_KEYS constant
# =============================================================================


def test_required_keys_contains_all_fields():
    assert _REQUIRED_KEYS == frozenset({
        "total_documents",
        "total_entities",
        "top_entities",
        "last_sync",
        "version",
    })


# =============================================================================
# update_knowledge_graph_summary tests (with mocked Supabase + ContextService)
# =============================================================================


@pytest.mark.asyncio
class TestUpdateKnowledgeGraphSummary:
    """Integration-level unit tests with mocked Supabase and ContextService."""

    @pytest.fixture(autouse=True)
    def _setup_mocks(self):
        """Reset mock state before each test."""
        self.mock_db = MagicMock()
        self.mock_context_service = MagicMock()

    # --- Success path -------------------------------------------------------

    async def test_update_success(self, client_id, valid_summary):
        """Happy path: read existing AT, merge, update, invalidate cache."""
        # Mock Supabase responses
        existing = {"tier": "BASIC", "enabled_tool_names": ["sql"]}
        select_response = MagicMock()
        select_response.data = {"available_tools": existing}
        select_response.execute = AsyncMock()

        update_result = MagicMock()
        update_result.data = [{"client_id": str(client_id)}]
        update_result.execute = AsyncMock()

        # Chain: db.table("clientes_blu").select("available_tools")...
        self.mock_db.table.return_value = self.mock_db
        self.mock_db.select.return_value = self.mock_db
        self.mock_db.eq.return_value = self.mock_db
        self.mock_db.maybe_single.return_value = self.mock_db
        self.mock_db.execute = AsyncMock(return_value=select_response)

        # Chain: db.table("clientes_blu").update(...)...
        mock_update_chain = MagicMock()
        mock_update_chain.eq.return_value = mock_update_chain
        mock_update_chain.execute = AsyncMock(return_value=update_result)
        self.mock_db.update.return_value = mock_update_chain

        # Mock context service cache invalidation
        self.mock_context_service.clear_context_cache = AsyncMock()

        with (
            patch(
                "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_supabase_client",
                return_value=self.mock_db,
            ),
            patch(
                "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_context_service",
                return_value=self.mock_context_service,
            ),
        ):
            result = await update_knowledge_graph_summary(client_id, valid_summary)

        assert result is True
        # Verify merge preserved existing fields
        update_call_args = self.mock_db.update.call_args
        assert update_call_args is not None
        updated_available_tools = update_call_args[0][0]["available_tools"]
        assert updated_available_tools["tier"] == "BASIC"
        assert updated_available_tools["enabled_tool_names"] == ["sql"]
        assert updated_available_tools["knowledge_graph_summary"] == valid_summary
        # Verify cache invalidation
        self.mock_context_service.clear_context_cache.assert_awaited_once_with(client_id)

    # --- Client not found ---------------------------------------------------

    async def test_update_client_not_found(self, client_id, valid_summary):
        """Returns False when Supabase returns no data (client missing)."""
        select_response = MagicMock()
        select_response.data = None  # maybe_single() returns None

        self.mock_db.table.return_value = self.mock_db
        self.mock_db.select.return_value = self.mock_db
        self.mock_db.eq.return_value = self.mock_db
        self.mock_db.maybe_single.return_value = self.mock_db
        self.mock_db.execute = AsyncMock(return_value=select_response)

        with patch(
            "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_supabase_client",
            return_value=self.mock_db,
        ):
            result = await update_knowledge_graph_summary(client_id, valid_summary)

        assert result is False
        # update() must not have been called
        self.mock_db.update.assert_not_called()

    # --- Supabase read error (RLS / network) --------------------------------

    async def test_update_rls_select_error(self, client_id, valid_summary):
        """Returns False when Supabase select raises (e.g., RLS/permission error)."""
        self.mock_db.table.return_value = self.mock_db
        self.mock_db.select.return_value = self.mock_db
        self.mock_db.eq.return_value = self.mock_db
        self.mock_db.maybe_single.return_value = self.mock_db
        self.mock_db.execute = AsyncMock(
            side_effect=Exception("permission denied for table clientes_blu")
        )

        with patch(
            "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_supabase_client",
            return_value=self.mock_db,
        ):
            result = await update_knowledge_graph_summary(client_id, valid_summary)

        assert result is False
        self.mock_db.update.assert_not_called()

    # --- Cache invalidation failure is non-fatal ----------------------------

    async def test_cache_invalidation_failure_is_non_fatal(self, client_id, valid_summary):
        """Update still returns True even when cache invalidation fails."""
        select_response = MagicMock()
        select_response.data = {"available_tools": {}}

        update_result = MagicMock()
        update_result.data = [{"client_id": str(client_id)}]

        self.mock_db.table.return_value = self.mock_db
        self.mock_db.select.return_value = self.mock_db
        self.mock_db.eq.return_value = self.mock_db
        self.mock_db.maybe_single.return_value = self.mock_db
        self.mock_db.execute = AsyncMock(return_value=select_response)

        mock_update_chain = MagicMock()
        mock_update_chain.eq.return_value = mock_update_chain
        mock_update_chain.execute = AsyncMock(return_value=update_result)
        self.mock_db.update.return_value = mock_update_chain

        self.mock_context_service.clear_context_cache = AsyncMock(
            side_effect=Exception("Redis connection refused")
        )

        with (
            patch(
                "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_supabase_client",
                return_value=self.mock_db,
            ),
            patch(
                "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_context_service",
                return_value=self.mock_context_service,
            ),
        ):
            result = await update_knowledge_graph_summary(client_id, valid_summary)

        assert result is True

    # --- Empty available_tools → defaults to {} -----------------------------

    async def test_update_when_available_tools_is_none(self, client_id, valid_summary):
        """available_tools None → treated as empty dict."""
        select_response = MagicMock()
        select_response.data = {"available_tools": None}

        update_result = MagicMock()
        update_result.data = [{"client_id": str(client_id)}]

        self.mock_db.table.return_value = self.mock_db
        self.mock_db.select.return_value = self.mock_db
        self.mock_db.eq.return_value = self.mock_db
        self.mock_db.maybe_single.return_value = self.mock_db
        self.mock_db.execute = AsyncMock(return_value=select_response)

        mock_update_chain = MagicMock()
        mock_update_chain.eq.return_value = mock_update_chain
        mock_update_chain.execute = AsyncMock(return_value=update_result)
        self.mock_db.update.return_value = mock_update_chain

        self.mock_context_service.clear_context_cache = AsyncMock()

        with (
            patch(
                "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_supabase_client",
                return_value=self.mock_db,
            ),
            patch(
                "tool_pool_api.server.tool_modules.knowledge_graph_sync.get_context_service",
                return_value=self.mock_context_service,
            ),
        ):
            result = await update_knowledge_graph_summary(client_id, valid_summary)

        assert result is True
        update_call_args = self.mock_db.update.call_args
        updated = update_call_args[0][0]["available_tools"]
        assert updated["knowledge_graph_summary"] == valid_summary
