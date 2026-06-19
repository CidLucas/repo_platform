"""Phase 5 (T5.1) — Business Memory REST endpoint for the dashboard.

Serves business memory data from the ``shared_business_memory`` table
for the frontend "Página de visualização de Memória do Negócio".

Routes (prefix ``/api``):
    GET  /business-memory        list all business memory records
    GET  /business-memory/{id}   fetch a single record by UUID
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from blu_auth.core.models import AuthResult
from blu_supabase_client import get_supabase_client
from tool_pool_api.api.integrations_router import _get_auth_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Business Memory"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BusinessMemoryRecord(BaseModel):
    """A single row from shared_business_memory."""

    id: str
    entity_type: str
    entity_name: str
    key: str
    value: dict | None = None
    metadata: dict | None = None
    source: str | None = None
    confidence: float | None = None
    version: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class BusinessMemoryListResponse(BaseModel):
    """Response wrapper for the business memory list endpoint."""

    client_id: str
    total_records: int
    records: list[BusinessMemoryRecord]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/business-memory", response_model=BusinessMemoryListResponse)
async def list_business_memory(
    entity_type: str | None = Query(
        None,
        description="Optional filter — skill, client, contact, supplier, user, snapshot, routine, agent_result, agent_metadata",
    ),
    entity_name: str | None = Query(
        None,
        description="Optional filter by entity name (case-insensitive prefix match)",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    auth: AuthResult = Depends(_get_auth_result),
) -> BusinessMemoryListResponse:
    """List business memory records for the authenticated client.

    Returns all records from ``shared_business_memory``, ordered by
    ``entity_type``, ``entity_name``, ``key``.  Supports optional
    filtering by ``entity_type`` and/or ``entity_name``.
    """
    client_id = str(auth.client_id)
    db = get_supabase_client()

    logger.info(
        "business_memory.list client_id=%s entity_type=%s entity_name=%s",
        client_id,
        entity_type,
        entity_name,
    )

    try:
        query = (
            db.schema("public")
            .table("shared_business_memory")
            .select("*")
            .eq("client_id", client_id)
            .order("entity_type, entity_name, key")
            .range(offset, offset + limit - 1)
        )

        if entity_type:
            query = query.eq("entity_type", entity_type)
        if entity_name:
            query = query.ilike("entity_name", f"{entity_name}%")

        result = query.execute()
    except Exception as exc:
        logger.exception(
            "business_memory.list failed for client=%s", client_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query business memory: {exc}",
        ) from exc

    rows = result.data if result.data else []

    records: list[BusinessMemoryRecord] = []
    for row in rows:
        records.append(
            BusinessMemoryRecord(
                id=row["id"],
                entity_type=row["entity_type"],
                entity_name=row["entity_name"],
                key=row["key"],
                value=row.get("value"),
                metadata=row.get("metadata", {}),
                source=row.get("source"),
                confidence=float(row["confidence"])
                if row.get("confidence")
                else None,
                version=row.get("version", 1),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )

    logger.info(
        "business_memory.list complete: %d records for client=%s",
        len(records),
        client_id,
    )

    return BusinessMemoryListResponse(
        client_id=client_id,
        total_records=len(records),
        records=records,
    )


@router.get(
    "/business-memory/{record_id}",
    response_model=BusinessMemoryRecord,
)
async def get_business_memory_record(
    record_id: str,
    auth: AuthResult = Depends(_get_auth_result),
) -> BusinessMemoryRecord:
    """Fetch a single business memory record by its UUID."""
    client_id = str(auth.client_id)

    # Validate UUID format
    try:
        UUID(record_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record ID format: '{record_id}'. Must be a valid UUID.",
        )

    db = get_supabase_client()

    try:
        result = (
            db.schema("public")
            .table("shared_business_memory")
            .select("*")
            .eq("id", record_id)
            .eq("client_id", client_id)
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Record not found: {exc}",
        ) from exc

    row = result.data
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Business memory record '{record_id}' not found.",
        )

    return BusinessMemoryRecord(
        id=row["id"],
        entity_type=row["entity_type"],
        entity_name=row["entity_name"],
        key=row["key"],
        value=row.get("value"),
        metadata=row.get("metadata", {}),
        source=row.get("source"),
        confidence=float(row["confidence"])
        if row.get("confidence")
        else None,
        version=row.get("version", 1),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
