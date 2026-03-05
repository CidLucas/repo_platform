"""Custom LangChain retriever backed by Supabase vector_db.

Calls the `search-documents` Edge Function to embed a query and
perform cosine-similarity search against ``vector_db.document_chunks``.
"""

import json
import logging
from typing import Any

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


class SupabaseVectorRetriever(BaseRetriever):
    """Retrieves documents from Supabase vector_db via the search-documents Edge Function."""

    supabase_url: str = Field(description="Supabase project URL")
    supabase_service_key: str = Field(description="Service role key for auth")
    client_id: str = Field(description="Client UUID for RLS filtering")
    match_count: int = Field(default=5)
    match_threshold: float = Field(default=0.5)
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document UUIDs to scope search to specific documents",
    )

    def _build_payload(self, query: str) -> dict[str, Any]:
        """Build the JSON payload for the search-documents Edge Function."""
        payload: dict[str, Any] = {
            "query": query,
            "client_id": self.client_id,
            "match_count": self.match_count,
            "match_threshold": self.match_threshold,
        }
        if self.document_ids:
            payload["document_ids"] = self.document_ids
        return payload

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
        """Call search-documents Edge Function and convert to LangChain Documents."""
        logger.debug(
            f"[SupabaseVectorRetriever] Searching for client {self.client_id}: '{query[:80]}...'"
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
        logger.debug(
            f"[SupabaseVectorRetriever] Got {len(results)} results for client {self.client_id}"
        )
        return _build_documents(results)

    # ── Async retrieval (used by .ainvoke()) ─────────────────

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """Async version — uses httpx.AsyncClient to avoid blocking the event loop."""
        logger.debug(
            f"[SupabaseVectorRetriever] Async searching for client {self.client_id}: '{query[:80]}...'"
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
            f"[SupabaseVectorRetriever] Async got {len(results)} results for client {self.client_id}"
        )
        return _build_documents(results)
