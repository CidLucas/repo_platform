"""search-documents HTTP router — replaces supabase/functions/search-documents/.

Mounted at /v1/search-documents in services/tool_pool_api/src/tool_pool_api/main.py.

The response shape is byte-for-byte compatible with the Deno EF that
this replaces, so the 2 Python callers
(``tool_pool_api.server.resources.execute_rag_cliente`` and
``blu_rag_factory.retriever.HybridRetriever``) keep working without
changes to their response parsing — only the URL changes.

Auth: service-role Bearer. Matches the Deno EF auth posture
(``isSystemInvocation`` in config.toml → no user JWT). Public callers
(frontend) MUST go through ``execute_rag_cliente`` which has its own
RBAC; they never call this endpoint directly.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from blu_supabase_client import get_supabase_client

from tool_pool_api.services.search_documents import search_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/search-documents", tags=["Vector Search"])


def _get_db() -> Any:
    return get_supabase_client(use_service_role=True)


@router.post("")
async def search_documents_endpoint(
    request: Request,
    db: Any = Depends(_get_db),
) -> dict[str, Any]:
    """Embed query and call ``vector_db.hybrid_match_documents`` / ``match_documents``.

    Body: { "query", "client_id", "match_count"?, "match_threshold"?,
            "search_mode"?, "fusion_strategy"?, "keyword_weight"?, "vector_weight"?,
            "scope"?, "categories"?, "themes"?, "document_ids"? }
    Response: { "results": [...] }
    """
    start = time.monotonic()
    body = await request.json()

    try:
        result = search_documents(
            db,
            query=body.get("query"),
            client_id=body.get("client_id"),
            match_count=body.get("match_count", 5),
            match_threshold=body.get("match_threshold", 0.3),
            document_ids=body.get("document_ids"),
            search_mode=body.get("search_mode", "hybrid"),
            fusion_strategy=body.get("fusion_strategy", "rrf"),
            keyword_weight=body.get("keyword_weight", 0.4),
            vector_weight=body.get("vector_weight", 0.6),
            scope=body.get("scope"),
            categories=body.get("categories"),
            themes=body.get("themes"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "error_code": "INVALID_INPUT"},
        )
    except RuntimeError as e:
        logger.error("search-documents runtime error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal error", "details": str(e), "error_code": "INTERNAL"},
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "search-docs client=%s mode=%s count=%d in %dms",
        body.get("client_id"),
        body.get("search_mode", "hybrid"),
        len(result.get("results", [])),
        duration_ms,
    )
    return result
