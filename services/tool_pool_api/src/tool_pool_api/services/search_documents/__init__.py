"""search-documents Python port — replaces supabase/functions/search-documents/.

Mirrors the Deno EF logic 1:1:
- Embeds the query text with Cohere embed-multilingual-light-v3.0 (384 dims).
- Calls ``vector_db.hybrid_match_documents`` (default, hybrid) or
  ``vector_db.match_documents`` (legacy, semantic) via ``supabase.rpc(...)``.
- Returns ``{"results": [...]}`` — byte-for-byte compatible with the EF.

Callers:
- ``services.tool_pool_api.server.resources.execute_rag_cliente`` (RAG tool)
- ``libs.blu_rag_factory.retriever`` (SupabaseVectorRetriever / HybridRetriever)

Both go through the FastAPI router at ``/v1/search-documents`` — they
don't import this module directly. The router is the single HTTP entry
point; this module is the in-process engine.

Auth posture: service-role only. Matches the Deno EF (``isSystemInvocation``
in config.toml → no user JWT). Public callers (frontend) MUST go through
``execute_rag_cliente`` which has its own RBAC.

⚠️ CRITICAL — Function signature drift
---------------------------------------
The Deno EF calls ``vector_db.hybrid_match_documents`` with **12 params**
(scope, categories, themes, fusion_strategy, weights, …). The function
in ``archive/20260430000000_baseline.sql:2692`` has **5 params** and the
active baseline ``20260523999999_baseline_v2.sql`` doesn't define the
function at all. This means the EF has been returning 500 in production
silently, and so will this port — until the function is re-applied with
the 12-param signature. The port is intentionally a drop-in replacement
of the EF (callers are unchanged) so re-applying the function in a future
migration makes the whole stack come back to life.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ── Embedding config (must match process-document EF) ──────────────
COHERE_EMBEDDING_MODEL = "embed-multilingual-light-v3.0"
EMBEDDING_DIMENSIONS = 384

VALID_SEARCH_MODES = frozenset({"semantic", "hybrid"})
VALID_FUSION_STRATEGIES = frozenset({"rrf", "weighted"})


def generate_embedding(text: str) -> list[float]:
    """Embed ``text`` via Cohere ``embed-multilingual-light-v3.0`` (384 dims).

    Uses the shared ``blu_llm_service`` client which reads ``CO_API_KEY``
    from the environment (same env var as the Deno EF used).

    Raises:
        ValueError: if ``CO_API_KEY`` is not set.
        RuntimeError: on Cohere API error.
    """
    try:
        from blu_llm_service import get_cohere_embedding_model
    except ImportError as exc:
        raise RuntimeError(
            "blu_llm_service não disponível para embedding vetorial. "
            "Verifique se o pacote está instalado."
        ) from exc

    embedder = get_cohere_embedding_model()
    embedding = embedder.embed_query(text.strip())

    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Cohere retornou {len(embedding)} dimensões, esperado {EMBEDDING_DIMENSIONS}. "
            f"Modelo: {COHERE_EMBEDDING_MODEL}"
        )

    return embedding


def _format_embedding(embedding: list[float]) -> str:
    """Format the embedding as a Postgres ``halfvec(384)`` literal.

    Example: ``[0.123,-0.456,…]``
    """
    return f"[{','.join(str(v) for v in embedding)}]"


def _build_doc_ids_param(document_ids: list[str] | None) -> str | None:
    """Build the ``{uuid,uuid,…}`` Postgres array literal, or NULL."""
    if document_ids and isinstance(document_ids, list) and len(document_ids) > 0:
        return "{" + ",".join(document_ids) + "}"
    return None


def _build_text_array_param(values: list[str] | None, default: str | None = None) -> str | None:
    """Build the ``{text,text,…}`` Postgres array literal, or NULL/default."""
    if values and isinstance(values, list) and len(values) > 0:
        return "{" + ",".join(values) + "}"
    if default is not None:
        return "{" + ",".join(default) + "}"
    return None


def _validate_inputs(
    query: str | None,
    client_id: str | None,
    search_mode: str,
    fusion_strategy: str,
) -> None:
    """Raise ``ValueError`` on missing/invalid input. Mirrors EF 400 responses."""
    if not query or not client_id:
        raise ValueError("Missing required fields: query, client_id")
    if search_mode not in VALID_SEARCH_MODES:
        raise ValueError(
            f"Invalid search_mode: {search_mode}. Must be 'semantic' or 'hybrid'."
        )
    if fusion_strategy not in VALID_FUSION_STRATEGIES:
        raise ValueError(
            f"Invalid fusion_strategy: {fusion_strategy}. Must be 'rrf' or 'weighted'."
        )


def search_documents(
    db: Any,
    *,
    query: str,
    client_id: str,
    match_count: int = 5,
    match_threshold: float = 0.3,
    document_ids: list[str] | None = None,
    search_mode: Literal["semantic", "hybrid"] = "hybrid",
    fusion_strategy: Literal["rrf", "weighted"] = "rrf",
    keyword_weight: float = 0.4,
    vector_weight: float = 0.6,
    scope: list[str] | None = None,
    categories: list[str] | None = None,
    themes: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Embed the query, call the vector RPC, return the hits.

    Returns:
        ``{"results": [{"id", "document_id", "content", "metadata",
        "similarity", ...}, ...]}`` — same shape as the Deno EF.

    Raises:
        ValueError: on bad input.
        RuntimeError: on Cohere or RPC error.
    """
    _validate_inputs(query, client_id, search_mode, fusion_strategy)

    # ── Logging: incoming parameters (mirrors EF) ─────────────
    logger.info(
        "[search-documents] Incoming params: %s",
        {
            "query": query[:120],
            "client_id": client_id,
            "search_mode": search_mode,
            "match_count": match_count,
            "match_threshold": match_threshold,
            "fusion_strategy": fusion_strategy,
            "keyword_weight": keyword_weight,
            "vector_weight": vector_weight,
            "scope": scope,
            "categories": categories,
            "themes": themes,
            "document_ids": document_ids,
        },
    )

    # 1. Embed query
    embed_start = time.monotonic()
    query_embedding = generate_embedding(query)
    embed_ms = (time.monotonic() - embed_start) * 1000
    first5 = ",".join(f"{v:.6f}" for v in query_embedding[:5])
    logger.info(
        "[search-documents] Cohere embed completed in %.1fms — dims=%d, first5=[%s]",
        embed_ms,
        len(query_embedding),
        first5,
    )

    embedding_str = _format_embedding(query_embedding)
    doc_ids_param = _build_doc_ids_param(document_ids)

    # 2. Call the SQL RPC
    rpc_start = time.monotonic()
    try:
        if search_mode == "semantic":
            result = db.rpc(
                "match_documents",
                {
                    "p_client_id": client_id,
                    "p_query_embed": embedding_str,
                    "p_match_count": match_count,
                    "p_match_threshold": match_threshold,
                    "p_document_ids": doc_ids_param,
                },
            ).execute()
        else:
            scope_param = _build_text_array_param(
                scope, default=["platform", "client"]
            )
            categories_param = _build_text_array_param(categories)
            themes_param = _build_text_array_param(themes)
            result = db.rpc(
                "hybrid_match_documents",
                {
                    "p_client_id": client_id,
                    "p_query_embed": embedding_str,
                    "p_query_text": query,
                    "p_match_count": match_count,
                    "p_match_threshold": match_threshold,
                    "p_document_ids": doc_ids_param,
                    "p_scope": scope_param,
                    "p_categories": categories_param,
                    "p_fusion_strategy": fusion_strategy,
                    "p_keyword_weight": keyword_weight,
                    "p_vector_weight": vector_weight,
                    "p_themes": themes_param,
                },
            ).execute()
    except Exception as exc:
        logger.error("[search-documents] RPC call failed: %s", exc, exc_info=True)
        raise RuntimeError(f"Vector RPC failed: {exc}") from exc

    rpc_ms = (time.monotonic() - rpc_start) * 1000
    rows = result.data or []
    logger.info(
        "[search-documents] SQL RPC completed in %.1fms — result_count=%d",
        rpc_ms,
        len(rows),
    )

    if rows:
        top3 = [
            {
                "rank": i + 1,
                "similarity": r.get("similarity"),
                "keyword_score": r.get("keyword_score"),
                "combined_score": r.get("combined_score"),
                "content_preview": (r.get("content") or "")[:60],
            }
            for i, r in enumerate(rows[:3])
        ]
        logger.info("[search-documents] Top-3 results: %s", top3)
    else:
        logger.warning(
            "[search-documents] EMPTY RESULTS — no chunks matched. query=%r client_id=%s mode=%s threshold=%s",
            query[:120],
            client_id,
            search_mode,
            match_threshold,
        )

    return {"results": rows}
