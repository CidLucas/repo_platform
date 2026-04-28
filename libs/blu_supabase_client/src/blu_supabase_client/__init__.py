"""
Blu Supabase Client - SDK wrapper for Supabase operations.

Provides a singleton client for database operations via Supabase REST API.
"""
from .auth_context import (
    AuthContext,
    JWTContextExtractor,
    get_jwt_extractor,
)
from .audit import (
    ActorKind,
    AuditError,
    Outcome,
    record_audit,
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
from .storage import (
    SupabaseStorage,
    UploadResult,
    get_storage,
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
    # Storage
    "SupabaseStorage",
    "UploadResult",
    "get_storage",
    # Audit log (Phase 0 / F0.4)
    "ActorKind",
    "AuditError",
    "Outcome",
    "record_audit",
]
