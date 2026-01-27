"""
CRUD operations for Supabase tables.

Replaces SQLAlchemy-based CRUD with Supabase SDK operations.
"""
import logging
from typing import Any
from uuid import UUID

from supabase import Client

from .client import get_supabase_client, set_rls_context

logger = logging.getLogger(__name__)


class SupabaseCRUD:
    """
    CRUD operations using Supabase SDK.

    Replaces vizu_db_connector.crud functions with Supabase REST API calls.
    """

    def __init__(self, client: Client | None = None):
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

    def get_cliente_vizu_by_api_key(self, api_key: str) -> dict[str, Any] | None:
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

    def get_cliente_vizu_by_id(self, cliente_id: UUID) -> dict[str, Any] | None:
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
    ) -> list[dict[str, Any]]:
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

    def create_cliente_vizu(self, data: dict[str, Any]) -> dict[str, Any] | None:
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
        data: dict[str, Any]
    ) -> dict[str, Any] | None:
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
        client_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get clientes finais for a cliente_vizu.

        Uses RLS context for automatic filtering.

        Args:
            client_id: UUID of the parent cliente_vizu
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            List of cliente_final dicts
        """
        try:
            # Set RLS context first
            set_rls_context(self.client, str(client_id))

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
        client_id: UUID,
        telefone: str
    ) -> dict[str, Any] | None:
        """
        Get cliente final by phone number.

        Args:
            client_id: UUID of the parent cliente_vizu
            telefone: Phone number to search

        Returns:
            Cliente final dict or None
        """
        try:
            # Set RLS context
            set_rls_context(self.client, str(client_id))

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
        client_id: UUID,
        cliente_final_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get mensagens with optional filtering by cliente_final.

        Args:
            client_id: UUID of the cliente_vizu (for RLS)
            cliente_final_id: Optional UUID to filter by cliente_final
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            List of mensagem dicts
        """
        try:
            # Set RLS context
            set_rls_context(self.client, str(client_id))

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
        client_id: UUID,
        data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Create a new mensagem.

        Args:
            client_id: UUID of the cliente_vizu (for RLS)
            data: Mensagem data dict

        Returns:
            Created mensagem dict or None
        """
        try:
            # Set RLS context
            set_rls_context(self.client, str(client_id))

            # Ensure client_id is in data for RLS
            data["client_id"] = str(client_id)

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
        params: dict[str, Any] | None = None
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

    # ========================================================================
    # INTEGRATION CONFIG OPERATIONS
    # ========================================================================

    def save_integration_config(
        self,
        client_id: UUID,
        provider: str,
        config_type: str,
        client_id_encrypted: str,
        client_secret_encrypted: str,
        redirect_uri: str,
        scopes: list,
    ) -> dict[str, Any] | None:
        """Save or update integration config."""
        try:
            data = {
                "client_id": str(client_id),
                "provider": provider,
                "config_type": config_type,
                "client_id_encrypted": client_id_encrypted,
                "client_secret_encrypted": client_secret_encrypted,
                "redirect_uri": redirect_uri,
                "scopes": scopes,
            }
            response = (
                self.client
                .table("integration_configs")
                .upsert(data, on_conflict="client_id,provider,config_type")
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error saving integration config: {e}")
            return None

    def get_integration_config(
        self,
        client_id: UUID,
        provider: str
    ) -> dict[str, Any] | None:
        """Get integration config."""
        try:
            response = (
                self.client
                .table("integration_configs")
                .select("*")
                .eq("client_id", str(client_id))
                .eq("provider", provider)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting integration config: {e}")
            return None

    # ========================================================================
    # INTEGRATION TOKENS OPERATIONS (Multi-account support)
    # ========================================================================

    def save_integration_tokens(
        self,
        client_id: UUID,
        provider: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str | None,
        token_type: str | None,
        expires_at: Any | None,
        scopes: list,
        metadata: dict | None = None,
        account_email: str | None = None,
        account_name: str | None = None,
        is_default: bool = False,
    ) -> dict[str, Any] | None:
        """Save or update integration tokens for a specific account."""
        try:
            # Use placeholder for legacy single-account usage
            if not account_email:
                account_email = "default@unknown.com"
                account_name = account_name or "Primary Account"
                is_default = True

            # If setting as default, clear other defaults first
            if is_default:
                self.client.table("integration_tokens").update(
                    {"is_default": False}
                ).eq("client_id", str(client_id)).eq(
                    "provider", provider
                ).eq("is_default", True).execute()

            data = {
                "client_id": str(client_id),
                "provider": provider,
                "access_token_encrypted": access_token_encrypted,
                "refresh_token_encrypted": refresh_token_encrypted,
                "token_type": token_type,
                "expires_at": expires_at.isoformat() if hasattr(expires_at, 'isoformat') else expires_at,
                "scopes": scopes,
                "metadata": metadata,
                "account_email": account_email,
                "account_name": account_name,
                "is_default": is_default,
            }
            response = (
                self.client
                .table("integration_tokens")
                .upsert(data, on_conflict="client_id,provider,account_email")
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error saving integration tokens: {e}")
            return None

    def get_integration_tokens(
        self,
        client_id: UUID,
        provider: str,
        account_email: str | None = None,
    ) -> dict[str, Any] | None:
        """Get integration tokens for a specific account or the default account."""
        try:
            if account_email:
                response = (
                    self.client
                    .table("integration_tokens")
                    .select("*")
                    .eq("client_id", str(client_id))
                    .eq("provider", provider)
                    .eq("account_email", account_email)
                    .limit(1)
                    .execute()
                )
            else:
                # Try default account first, then fall back to any account
                response = (
                    self.client
                    .table("integration_tokens")
                    .select("*")
                    .eq("client_id", str(client_id))
                    .eq("provider", provider)
                    .order("is_default", desc=True)
                    .order("created_at")
                    .limit(1)
                    .execute()
                )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting integration tokens: {e}")
            return None

    def list_integration_accounts(
        self,
        client_id: UUID,
        provider: str,
    ) -> list[dict[str, Any]]:
        """List all connected accounts for a cliente/provider."""
        try:
            response = (
                self.client
                .table("integration_tokens")
                .select("id,account_email,account_name,is_default,expires_at,scopes,created_at")
                .eq("client_id", str(client_id))
                .eq("provider", provider)
                .order("is_default", desc=True)
                .order("account_email")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing integration accounts: {e}")
            return []

    def set_default_account(
        self,
        client_id: UUID,
        provider: str,
        account_email: str,
    ) -> dict[str, Any] | None:
        """Set a specific account as the default for a cliente/provider."""
        try:
            # Clear existing default
            self.client.table("integration_tokens").update(
                {"is_default": False}
            ).eq("client_id", str(client_id)).eq(
                "provider", provider
            ).execute()

            # Set new default
            response = (
                self.client
                .table("integration_tokens")
                .update({"is_default": True})
                .eq("client_id", str(client_id))
                .eq("provider", provider)
                .eq("account_email", account_email)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error setting default account: {e}")
            return None

    def revoke_integration(
        self,
        client_id: UUID,
        provider: str,
        account_email: str | None = None,
    ) -> bool:
        """Revoke integration for a specific account or all accounts."""
        try:
            if account_email:
                self.client.table("integration_tokens").delete().eq(
                    "client_id", str(client_id)
                ).eq("provider", provider).eq("account_email", account_email).execute()
            else:
                # Revoke all accounts for this provider
                self.client.table("integration_tokens").delete().eq(
                    "client_id", str(client_id)
                ).eq("provider", provider).execute()
                self.client.table("integration_configs").delete().eq(
                    "client_id", str(client_id)
                ).eq("provider", provider).execute()
            return True
        except Exception as e:
            logger.error(f"Error revoking integration: {e}")
            return False

    # ========================================================================
    # PROMPT TEMPLATE OPERATIONS
    # ========================================================================

    def get_prompt_template(
        self,
        name: str,
        client_id: UUID | None = None,
        version: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Get a prompt template by name.

        Priority:
        1. Client-specific prompt (if client_id provided)
        2. Global prompt (client_id = NULL)

        Args:
            name: Prompt name (e.g., 'atendente/system')
            client_id: Optional client UUID for client-specific override
            version: Optional specific version (None = latest)

        Returns:
            Prompt template dict or None if not found
        """
        try:
            # Try client-specific prompt first
            if client_id:
                query = (
                    self.client
                    .table("prompt_template")
                    .select("*")
                    .eq("name", name)
                    .eq("client_id", str(client_id))
                    .eq("is_active", True)
                )

                if version:
                    query = query.eq("version", version)
                else:
                    query = query.order("version", desc=True)

                response = query.limit(1).execute()

                if response.data and len(response.data) > 0:
                    logger.debug(
                        f"Prompt '{name}' v{response.data[0].get('version')} "
                        f"found for client {client_id}"
                    )
                    return response.data[0]

            # Fallback: global prompt (client_id is NULL)
            query = (
                self.client
                .table("prompt_template")
                .select("*")
                .eq("name", name)
                .is_("client_id", "null")
                .eq("is_active", True)
            )

            if version:
                query = query.eq("version", version)
            else:
                query = query.order("version", desc=True)

            response = query.limit(1).execute()

            if response.data and len(response.data) > 0:
                logger.debug(f"Global prompt '{name}' v{response.data[0].get('version')} found")
                return response.data[0]

            return None

        except Exception as e:
            logger.warning(f"Error fetching prompt template '{name}': {e}")
            return None


# ============================================================================
# CONVENIENCE FUNCTIONS (backwards compatibility with old crud.py)
# ============================================================================

_crud_instance: SupabaseCRUD | None = None


def get_crud() -> SupabaseCRUD:
    """Get singleton CRUD instance."""
    global _crud_instance
    if _crud_instance is None:
        _crud_instance = SupabaseCRUD()
    return _crud_instance


def get_cliente_vizu_by_api_key(api_key: str) -> dict[str, Any] | None:
    """Convenience function matching old crud.py signature."""
    return get_crud().get_cliente_vizu_by_api_key(api_key)


def get_cliente_vizu_by_id(cliente_id: UUID) -> dict[str, Any] | None:
    """Convenience function matching old crud.py signature."""
    return get_crud().get_cliente_vizu_by_id(cliente_id)
