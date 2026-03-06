"""Custom LangChain retrievers backed by Supabase vector_db.

Provides:
- ``SupabaseVectorRetriever``: Pure semantic (cosine-similarity) search.
- ``HybridRetriever``: Hybrid semantic + keyword search with configurable fusion
  (RRF or weighted linear) via the ``hybrid_match_documents`` RPC.

Both call the ``search-documents`` Edge Function to embed queries and
search against ``vector_db.document_chunks``.
"""

import json
import logging
from typing import Any, Literal

import httpx
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

logger = logging.getLogger(__name__)


def _parse_result_metadata(result: dict[str, Any]) -> dict[str, Any]:
    """Parse a single search result into enriched Document metadata."""
    # Parse chunk metadata (handles both proper JSONB objects and legacy double-encoded strings)
    raw_meta = result.get("metadata")
    if isinstance(raw_meta, str):
        try:
            parsed = json.loads(raw_meta)
            # Handle double-encoded case: if still a string, parse again
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            chunk_meta = parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            chunk_meta = {}
    elif isinstance(raw_meta, dict):
        chunk_meta = raw_meta
    else:
        chunk_meta = {}

    # Build enriched metadata from chunk metadata + match_documents JOIN fields
    metadata = {
        **chunk_meta,
        "document_id": result.get("document_id"),
        "similarity": result.get("similarity"),
    }
    # Add file_name and document_title from the documents table JOIN (Phase B2)
    if result.get("file_name"):
        metadata["file_name"] = result["file_name"]
    if result.get("document_title"):
        metadata["document_title"] = result["document_title"]

    # Hybrid search fields (Phase 3)
    if result.get("keyword_score") is not None:
        metadata["keyword_score"] = result["keyword_score"]
    if result.get("combined_score") is not None:
        metadata["combined_score"] = result["combined_score"]
    if result.get("scope"):
        metadata["scope"] = result["scope"]
    if result.get("category"):
        metadata["category"] = result["category"]

    return metadata


def _build_documents(results: list[dict[str, Any]]) -> list[Document]:
    """Convert search-documents response results into LangChain Documents."""
    return [
        Document(
            page_content=result["content"],
            metadata=_parse_result_metadata(result),
        )
        for result in results
    ]


class _BaseSupabaseRetriever(BaseRetriever):
    """Shared base for Supabase vector_db retrievers.

    Provides common fields, HTTP helpers, and sync/async retrieval logic.
    Subclasses must override ``_build_payload`` and ``_log_prefix``.
    """

    supabase_url: str = Field(description="Supabase project URL")
    supabase_service_key: str = Field(description="Service role key for auth")
    client_id: str = Field(description="Client UUID for RLS filtering")
    match_count: int = Field(default=5)
    match_threshold: float = Field(default=0.5)
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document UUIDs to scope search to specific documents",
    )

    @property
    def _log_prefix(self) -> str:
        """Override in subclass for clearer log lines."""
        return self.__class__.__name__

    def _build_payload(self, query: str) -> dict[str, Any]:  # noqa: ARG002
        raise NotImplementedError

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.supabase_service_key}",
            "Content-Type": "application/json",
        }

    @property
    def _search_url(self) -> str:
        return f"{self.supabase_url}/functions/v1/search-documents"

    # ── Sync retrieval (used by .invoke()) ───────────────────

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        logger.debug(
            f"[{self._log_prefix}] Searching for client {self.client_id}: '{query[:80]}...'"
        )

        response = httpx.post(
            self._search_url,
            json=self._build_payload(query),
            headers=self._build_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        logger.debug(f"[{self._log_prefix}] Got {len(results)} results for client {self.client_id}")
        return _build_documents(results)

    # ── Async retrieval (used by .ainvoke()) ─────────────────

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        logger.debug(
            f"[{self._log_prefix}] Async searching for client {self.client_id}: '{query[:80]}...'"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._search_url,
                json=self._build_payload(query),
                headers=self._build_headers(),
            )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        logger.debug(
            f"[{self._log_prefix}] Async got {len(results)} results for client {self.client_id}"
        )
        return _build_documents(results)


class SupabaseVectorRetriever(_BaseSupabaseRetriever):
    """Retrieves documents from Supabase vector_db via the search-documents Edge Function.

    Pure semantic (cosine-similarity) search.
    """

    def _build_payload(self, query: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "client_id": self.client_id,
            "match_count": self.match_count,
            "match_threshold": self.match_threshold,
        }
        if self.document_ids:
            payload["document_ids"] = self.document_ids
        return payload


class HybridRetriever(_BaseSupabaseRetriever):
    """Hybrid retriever combining semantic + keyword search with configurable fusion.

    Calls the ``search-documents`` Edge Function with hybrid parameters which
    routes to the ``hybrid_match_documents`` RPC — fusing pgvector cosine
    similarity with PostgreSQL full-text search (``ts_rank``).

    Fusion strategies:
    - **rrf** (Reciprocal Rank Fusion): ``1/(k+rank_sem) + 1/(k+rank_kw)``, k=60
    - **weighted**: ``vector_weight * similarity + keyword_weight * keyword_score``
    """

    # Hybrid-specific parameters
    search_mode: Literal["semantic", "keyword", "hybrid"] = Field(
        default="hybrid",
        description="Search strategy: semantic-only, keyword-only, or hybrid fusion",
    )
    fusion_strategy: Literal["rrf", "weighted"] = Field(
        default="rrf",
        description="Score fusion method: reciprocal rank fusion or weighted linear",
    )
    keyword_weight: float = Field(
        default=0.4,
        description="Weight for keyword score in weighted fusion (0.0-1.0)",
    )
    vector_weight: float = Field(
        default=0.6,
        description="Weight for vector similarity in weighted fusion (0.0-1.0)",
    )
    scope: list[str] = Field(
        default_factory=lambda: ["platform", "client"],
        description="Document scopes to search: 'platform' (shared) and/or 'client' (tenant)",
    )
    categories: list[str] | None = Field(
        default=None,
        description="Optional category filter (e.g. 'tax_knowledge', 'dados_negocio')",
    )

    @property
    def _log_prefix(self) -> str:
        return f"HybridRetriever({self.search_mode}/{self.fusion_strategy})"

    def _build_payload(self, query: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "client_id": self.client_id,
            "match_count": self.match_count,
            "match_threshold": self.match_threshold,
            "search_mode": self.search_mode,
            "fusion_strategy": self.fusion_strategy,
            "keyword_weight": self.keyword_weight,
            "vector_weight": self.vector_weight,
            "scope": self.scope,
        }
        if self.document_ids:
            payload["document_ids"] = self.document_ids
        if self.categories:
            payload["categories"] = self.categories
        return payload
