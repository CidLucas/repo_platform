"""Tests for vizu_supabase_client."""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Set test environment before imports
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"


class TestSupabaseConfig:
    """Tests for SupabaseConfig."""

    def test_config_from_env(self):
        """Test loading config from environment variables."""
        from vizu_supabase_client.client import SupabaseConfig

        config = SupabaseConfig.from_env()
        assert config.url == "https://test.supabase.co"
        assert config.service_key == "test-service-key"

    def test_config_missing_url_raises(self):
        """Test that missing SUPABASE_URL raises ValueError."""
        from vizu_supabase_client.client import SupabaseConfig

        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": "key"}):
            # Clear the cached config
            os.environ.pop("SUPABASE_URL", None)
            with pytest.raises(ValueError, match="SUPABASE_URL is required"):
                SupabaseConfig.from_env()


class TestSupabaseCRUD:
    """Tests for SupabaseCRUD operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Supabase client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def crud(self, mock_client):
        """Create SupabaseCRUD with mock client."""
        from vizu_supabase_client.crud import SupabaseCRUD
        crud = SupabaseCRUD(client=mock_client)
        return crud

    def test_get_cliente_vizu_by_api_key_found(self, crud, mock_client):
        """Test fetching cliente by API key when found."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-uuid", "nome_empresa": "Test Corp"}]

        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        result = crud.get_cliente_vizu_by_api_key("test-key")

        assert result is not None
        assert result["id"] == "test-uuid"
        assert result["nome_empresa"] == "Test Corp"
        mock_client.table.assert_called_with("cliente_vizu")

    def test_get_cliente_vizu_by_api_key_not_found(self, crud, mock_client):
        """Test fetching cliente by API key when not found."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        result = crud.get_cliente_vizu_by_api_key("nonexistent-key")

        assert result is None

    def test_get_cliente_vizu_by_id(self, crud, mock_client):
        """Test fetching cliente by ID."""
        from uuid import UUID

        mock_response = MagicMock()
        mock_response.data = [{"id": "test-uuid", "nome_empresa": "Test Corp"}]

        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        result = crud.get_cliente_vizu_by_id(UUID("12345678-1234-1234-1234-123456789abc"))

        assert result is not None
        assert result["nome_empresa"] == "Test Corp"

    def test_create_cliente_vizu(self, crud, mock_client):
        """Test creating a new cliente."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "new-uuid", "nome_empresa": "New Corp"}]

        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = crud.create_cliente_vizu({"nome_empresa": "New Corp", "tipo_cliente": "AGENDAMENTO"})

        assert result is not None
        assert result["nome_empresa"] == "New Corp"

    def test_update_cliente_vizu(self, crud, mock_client):
        """Test updating a cliente."""
        from uuid import UUID

        mock_response = MagicMock()
        mock_response.data = [{"id": "test-uuid", "nome_empresa": "Updated Corp"}]

        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = crud.update_cliente_vizu(
            UUID("12345678-1234-1234-1234-123456789abc"),
            {"nome_empresa": "Updated Corp"}
        )

        assert result is not None
        assert result["nome_empresa"] == "Updated Corp"

    def test_delete_cliente_vizu(self, crud, mock_client):
        """Test deleting a cliente."""
        from uuid import UUID

        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        result = crud.delete_cliente_vizu(UUID("12345678-1234-1234-1234-123456789abc"))

        assert result is True


class TestRLSContext:
    """Tests for RLS context setting."""

    def test_set_rls_context(self):
        """Test setting RLS context via RPC."""
        from vizu_supabase_client.client import set_rls_context

        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = MagicMock()

        set_rls_context(mock_client, "test-cliente-uuid")

        mock_client.rpc.assert_called_with(
            "set_current_cliente_id",
            {"cliente_id": "test-cliente-uuid"}
        )
