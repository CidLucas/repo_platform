"""
Vizu Supabase Client - SDK wrapper for Supabase operations.

Provides a singleton client for database operations via Supabase REST API.
"""
from .client import (
    get_supabase_client,
    get_async_supabase_client,
    close_supabase_client,
    SupabaseConfig,
)
from .crud import SupabaseCRUD

__all__ = [
    "get_supabase_client",
    "get_async_supabase_client",
    "close_supabase_client",
    "SupabaseConfig",
    "SupabaseCRUD",
]
