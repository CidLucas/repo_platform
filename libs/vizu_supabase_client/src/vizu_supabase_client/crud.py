"""
CRUD operations for Supabase tables.

Replaces SQLAlchemy-based CRUD with Supabase SDK operations.
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from supabase import Client

from .client import get_supabase_client, set_rls_context

logger = logging.getLogger(__name__)


class SupabaseCRUD:
    """
    CRUD operations using Supabase SDK.

    Replaces vizu_db_connector.crud functions with Supabase REST API calls.
    """

    def __init__(self, client: Optional[Client] = None):
        """
        Initialize CRUD with optional client injection (for testing).

        Args:
            client: Supabase client. If None, uses singleton.
        """
        self._client = client

    @property
    def client(self) -> Client:
        """Get Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # ========================================================================
    # CLIENTE_VIZU OPERATIONS
    # ========================================================================

    def get_cliente_vizu_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch cliente by API Key (used in authentication).

        Args:
            api_key: The API key string

        Returns:
            Dict with cliente data or None if not found
        """
        try:
            response = (
                self.client
                .table("cliente_vizu")
                .select("*")
                .eq("api_key", api_key)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error fetching cliente by API key: {e}")
            return None

    def get_cliente_vizu_by_id(self, cliente_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Fetch cliente by ID.

        Args:
            cliente_id: UUID of the cliente

        Returns:
            Dict with cliente data or None if not found
        """
        try:
            response = (
                self.client
                .table("cliente_vizu")
                .select("*")
                .eq("id", str(cliente_id))
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error fetching cliente by ID: {e}")
            return None

    def list_clientes_vizu(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all clientes with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            List of cliente dicts
        """
        try:
            response = (
                self.client
                .table("cliente_vizu")
                .select("*")
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Error listing clientes: {e}")
            return []

    def create_cliente_vizu(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new cliente.

        Args:
            data: Dict with cliente fields (nome_empresa, tipo_cliente, tier, etc.)

        Returns:
            Created cliente dict or None on error
        """
        try:
            response = (
                self.client
                .table("cliente_vizu")
                .insert(data)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error creating cliente: {e}")
            return None

    def update_cliente_vizu(
        self,
        cliente_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a cliente.

        Args:
            cliente_id: UUID of the cliente to update
            data: Dict with fields to update

        Returns:
            Updated cliente dict or None on error
        """
        try:
            response = (
                self.client
                .table("cliente_vizu")
                .update(data)
                .eq("id", str(cliente_id))
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error updating cliente: {e}")
            return None

    def delete_cliente_vizu(self, cliente_id: UUID) -> bool:
        """
        Delete a cliente.

        Args:
            cliente_id: UUID of the cliente to delete

        Returns:
            True if deleted, False on error
        """
        try:
            self.client.table("cliente_vizu").delete().eq("id", str(cliente_id)).execute()
            return True

        except Exception as e:
            logger.error(f"Error deleting cliente: {e}")
            return False

    # ========================================================================
    # CLIENTE_FINAL OPERATIONS (with RLS)
    # ========================================================================

    def get_clientes_finais(
        self,
        cliente_vizu_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get clientes finais for a cliente_vizu.

        Uses RLS context for automatic filtering.

        Args:
            cliente_vizu_id: UUID of the parent cliente_vizu
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            List of cliente_final dicts
        """
        try:
            # Set RLS context first
            set_rls_context(self.client, str(cliente_vizu_id))

            response = (
                self.client
                .table("cliente_final")
                .select("*")
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching clientes finais: {e}")
            return []

    def get_cliente_final_by_phone(
        self,
        cliente_vizu_id: UUID,
        telefone: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cliente final by phone number.

        Args:
            cliente_vizu_id: UUID of the parent cliente_vizu
            telefone: Phone number to search

        Returns:
            Cliente final dict or None
        """
        try:
            # Set RLS context
            set_rls_context(self.client, str(cliente_vizu_id))

            response = (
                self.client
                .table("cliente_final")
                .select("*")
                .eq("telefone", telefone)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error fetching cliente final by phone: {e}")
            return None

    # ========================================================================
    # MENSAGEM OPERATIONS (with RLS)
    # ========================================================================

    def get_mensagens(
        self,
        cliente_vizu_id: UUID,
        cliente_final_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get mensagens with optional filtering by cliente_final.

        Args:
            cliente_vizu_id: UUID of the cliente_vizu (for RLS)
            cliente_final_id: Optional UUID to filter by cliente_final
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            List of mensagem dicts
        """
        try:
            # Set RLS context
            set_rls_context(self.client, str(cliente_vizu_id))

            query = (
                self.client
                .table("mensagem")
                .select("*")
            )

            if cliente_final_id:
                query = query.eq("cliente_final_id", str(cliente_final_id))

            response = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching mensagens: {e}")
            return []

    def create_mensagem(
        self,
        cliente_vizu_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new mensagem.

        Args:
            cliente_vizu_id: UUID of the cliente_vizu (for RLS)
            data: Mensagem data dict

        Returns:
            Created mensagem dict or None
        """
        try:
            # Set RLS context
            set_rls_context(self.client, str(cliente_vizu_id))

            # Ensure cliente_vizu_id is in data for RLS
            data["cliente_vizu_id"] = str(cliente_vizu_id)

            response = (
                self.client
                .table("mensagem")
                .insert(data)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error creating mensagem: {e}")
            return None

    # ========================================================================
    # RPC HELPERS
    # ========================================================================

    def call_function(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Call a PostgreSQL function via RPC.

        Args:
            function_name: Name of the Postgres function
            params: Parameters to pass to the function

        Returns:
            Function result
        """
        try:
            response = self.client.rpc(function_name, params or {}).execute()
            return response.data

        except Exception as e:
            logger.error(f"Error calling function {function_name}: {e}")
            return None


# ============================================================================
# CONVENIENCE FUNCTIONS (backwards compatibility with old crud.py)
# ============================================================================

_crud_instance: Optional[SupabaseCRUD] = None


def get_crud() -> SupabaseCRUD:
    """Get singleton CRUD instance."""
    global _crud_instance
    if _crud_instance is None:
        _crud_instance = SupabaseCRUD()
    return _crud_instance


def get_cliente_vizu_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Convenience function matching old crud.py signature."""
    return get_crud().get_cliente_vizu_by_api_key(api_key)


def get_cliente_vizu_by_id(cliente_id: UUID) -> Optional[Dict[str, Any]]:
    """Convenience function matching old crud.py signature."""
    return get_crud().get_cliente_vizu_by_id(cliente_id)
