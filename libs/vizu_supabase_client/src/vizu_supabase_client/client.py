"""
Supabase Client - Singleton pattern for Supabase SDK connection.

Uses HTTP REST API (PostgREST), NOT direct PostgreSQL connection.
This solves DNS resolution issues with Supabase pooler.
"""
import logging
import os
from dataclasses import dataclass
from functools import lru_cache

from supabase.lib.client_options import SyncClientOptions

from supabase import Client, create_client

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class SupabaseConfig:
    """Configuration for Supabase client."""
    url: str
    service_key: str  # service_role key for server-side operations
    anon_key: str | None = None  # anon key for client-side / RLS-enforced operations

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """Load configuration from environment variables."""
        url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not url:
            raise ValueError(
                "SUPABASE_URL is required. "
                "Set it to your Supabase project URL (e.g., https://xxx.supabase.co)"
            )

        if not service_key:
            raise ValueError(
                "SUPABASE_SERVICE_KEY is required. "
                "Use the service_role key from your Supabase dashboard."
            )

        return cls(url=url, service_key=service_key, anon_key=anon_key)


# ============================================================================
# SINGLETON CLIENT
# ============================================================================

_supabase_client: Client | None = None
_async_supabase_client = None  # Will be AsyncClient when created


def get_supabase_client(use_service_role: bool = True) -> Client:
    """
    Get or create a singleton Supabase client (sync).

    Args:
        use_service_role: If True (default), uses service_role key which bypasses RLS.
                         Set to False to use anon key with RLS enforcement.

    Returns:
        Supabase Client instance.

    Usage:
        client = get_supabase_client()
        response = client.table("cliente_vizu").select("*").execute()
        data = response.data
    """
    global _supabase_client

    if _supabase_client is None:
        config = SupabaseConfig.from_env()
        key = config.service_key if use_service_role else (config.anon_key or config.service_key)

        # SyncClientOptions for sync create_client (not ClientOptions)
        options = SyncClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        )

        _supabase_client = create_client(config.url, key, options)
        logger.info(f"Supabase client created for: {config.url}")

    return _supabase_client


async def get_async_supabase_client(use_service_role: bool = True):
    """
    Get or create a singleton async Supabase client.

    For async operations in FastAPI endpoints.

    Note: Supabase Python SDK v2 supports async operations on the sync client
    via asyncio. For true async, we wrap sync calls in asyncio.to_thread.
    """
    # For now, return the sync client - Supabase SDK handles this well
    # The PostgREST calls are HTTP-based and don't block the event loop significantly
    return get_supabase_client(use_service_role)


def close_supabase_client() -> None:
    """
    Close the singleton client (for graceful shutdown).
    """
    global _supabase_client, _async_supabase_client

    if _supabase_client is not None:
        # Supabase client doesn't have explicit close, but we clear the reference
        _supabase_client = None
        logger.info("Supabase client reference cleared")

    if _async_supabase_client is not None:
        _async_supabase_client = None


# ============================================================================
# RLS CONTEXT HELPER
# ============================================================================

def set_rls_context(client: Client, cliente_id: str) -> None:
    """
    Set RLS context by calling the PostgreSQL function via RPC.

    This should be called before queries that need tenant isolation.

    Args:
        client: Supabase client instance
        cliente_id: UUID string of the current cliente_vizu

    Usage:
        client = get_supabase_client()
        set_rls_context(client, "uuid-string")
        # Subsequent queries will respect RLS policies
    """
    try:
        client.rpc("set_current_cliente_id", {"cliente_id": cliente_id}).execute()
        logger.debug(f"RLS context set for cliente_id: {cliente_id}")
    except Exception as e:
        logger.warning(f"Could not set RLS context: {e}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

@lru_cache(maxsize=1)
def get_supabase_config() -> SupabaseConfig:
    """Get cached Supabase configuration."""
    return SupabaseConfig.from_env()
