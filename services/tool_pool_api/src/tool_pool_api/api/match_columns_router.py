"""
match-columns HTTP router — replaces supabase/functions/match-columns/.

Mounted at /v1/match-columns in services/tool_pool_api/src/tool_pool_api/main.py.

The response shape is byte-for-byte compatible with the Deno EF that
this replaces, so the 2 TS callers (upload-csv-source, upload-drive-source
edge functions) and 1 Python caller (tool_pool_api context_module) keep
working without changes to their response parsing.

Auth: service-role Bearer (the endpoint is called by 2 EFs and 1 Python
service via service-role key; user JWT is rejected). This matches the
auth posture of the Deno EF (isSystemInvocation OR requireAuth — but in
practice all 3 callers are service-role).
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from blu_supabase_client import get_supabase_client

from tool_pool_api.services.match_columns import (
    match_columns as match_columns_logic,
    VALID_SCHEMA_TYPES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/match-columns", tags=["Schema Matching"])


def _get_db() -> Any:
    return get_supabase_client(use_service_role=True)


@router.post("")
async def match_columns_endpoint(
    request: Request,
    db: Any = Depends(_get_db),
) -> dict[str, Any]:
    """Match source columns against the canonical schema.

    Body: { "source_columns": [...], "schema_type": "invoices" | "fato_transacoes" | "dim_clientes" | "dim_inventory" }
    Response: { matched, unmatched, needs_review, confidence_scores, detected_context }
    """
    start = time.monotonic()
    body = await request.json()
    source_columns = body.get("source_columns")
    schema_type = body.get("schema_type", "invoices")

    if not source_columns or not isinstance(source_columns, list):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "source_columns must be a non-empty array",
                "error_code": "INVALID_INPUT",
            },
        )

    if schema_type not in VALID_SCHEMA_TYPES:
        schema_type = "invoices"

    try:
        result = match_columns_logic(db, source_columns, schema_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e), "error_code": "INVALID_INPUT"})
    except RuntimeError as e:
        logger.error("match-columns canonical load failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"error": "Could not load canonical schema", "error_code": "SCHEMA_LOAD_ERROR"},
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "matched cols=%d matched=%d needs_review=%d unmatched=%d in %dms (schema=%s ctx=%s)",
        len(source_columns),
        len(result.matched),
        len(result.needs_review),
        len(result.unmatched),
        duration_ms,
        schema_type,
        result.detected_context,
    )
    return result.to_dict()
