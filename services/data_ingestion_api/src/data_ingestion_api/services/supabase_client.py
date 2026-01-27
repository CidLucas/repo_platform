"""Thin adapter that re-uses the shared `vizu_supabase_client` package.

This module keeps the previous async-friendly interface used by the
`data_ingestion_api` code but delegates all behaviour to the common
`vizu_supabase_client` client. That avoids duplicated connection logic
and centralizes RLS helpers.
"""

import logging
from typing import Any

from vizu_supabase_client.client import (
    get_supabase_client as _get_shared_supabase_client,
)
from vizu_supabase_client.client import set_rls_context

logger = logging.getLogger(__name__)


async def insert(table: str, data: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Insert record(s) into a table.

    Args:
        table: Table name
        data: Single record (dict) or list of records (list of dicts)

    Returns:
        Inserted record(s) - single dict or list of dicts
    """
    client = _get_shared_supabase_client()
    resp = client.table(table).insert(data).execute()

    # Return appropriate format based on input
    if isinstance(data, list):
        return resp.data if resp.data else []
    else:
        return resp.data[0] if resp.data else {}


async def upsert(table: str, data: dict[str, Any], on_conflict: str = "id") -> dict[str, Any]:
    client = _get_shared_supabase_client()
    resp = client.table(table).upsert(data, on_conflict=on_conflict).execute()
    return resp.data[0] if resp.data else {}


async def select(table: str, columns: str = "*", filters: dict[str, Any] | None = None, client_id: str | None = None) -> list[dict[str, Any]]:
    client = _get_shared_supabase_client()

    # If caller provides a client id, set RLS context for client-scoped tables
    if client_id:
        try:
            set_rls_context(client, str(client_id))
        except Exception:
            logger.debug("Failed to set RLS context; continuing without it")

    query = client.table(table).select(columns)
    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)

    resp = query.execute()
    return resp.data or []


async def select_one(table: str, columns: str = "*", filters: dict[str, Any] | None = None, client_id: str | None = None) -> dict[str, Any] | None:
    res = await select(table, columns, filters, client_id)
    return res[0] if res else None


async def update(table: str, data: dict[str, Any], filters: dict[str, Any]) -> list[dict[str, Any]]:
    client = _get_shared_supabase_client()
    query = client.table(table).update(data)
    for col, val in filters.items():
        query = query.eq(col, val)
    resp = query.execute()
    return resp.data or []


async def delete(table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
    client = _get_shared_supabase_client()
    query = client.table(table).delete()
    for col, val in filters.items():
        query = query.eq(col, val)
    resp = query.execute()
    return resp.data or []
