"""
Blu Supabase Client - SDK wrapper for Supabase operations.

Provides a singleton client for database operations via Supabase REST API.
"""
from __future__ import annotations
from .auth_context import (
    AuthContext,
    JWTContextExtractor,
    get_jwt_extractor,
)
from blu_supabase_client.audit import (
    ActorKind,
    AuditError,
    Outcome,
    record_audit,
)
from blu_supabase_client.client import (
    SupabaseConfig,
    close_supabase_client,
    get_async_supabase_client,
    get_supabase_client,
)
from blu_supabase_client.crud import SupabaseCRUD
from blu_supabase_client.postgrest_executor import (
    PostgRESTQueryExecutor,
    QueryResult,
    get_postgrest_executor,
)
from blu_supabase_client.storage import (
    SupabaseStorage,
    UploadResult,
    get_storage,
)
from blu_supabase_client.db_engine import (
    get_direct_engine,
    get_pooler_engine,
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
    "get_direct_engine",
    "get_pooler_engine",
]
