"""
Vizu Supabase Client - SDK wrapper for Supabase operations.

Provides a singleton client for database operations via Supabase REST API.
"""
from .auth_context import (
    AuthContext,
    JWTContextExtractor,
    get_jwt_extractor,
)
from .client import (
    SupabaseConfig,
    close_supabase_client,
    get_async_supabase_client,
    get_supabase_client,
)
from .crud import SupabaseCRUD
from .postgrest_executor import (
    PostgRESTQueryExecutor,
    QueryResult,
    get_postgrest_executor,
)

__all__ = [
    # Client
    "get_supabase_client",
    "get_async_supabase_client",
    "close_supabase_client",
    "SupabaseConfig",
    # CRUD
    "SupabaseCRUD",
    # Auth Context
    "AuthContext",
    "JWTContextExtractor",
    "get_jwt_extractor",
    # PostgREST Executor
    "QueryResult",
    "PostgRESTQueryExecutor",
    "get_postgrest_executor",
]
