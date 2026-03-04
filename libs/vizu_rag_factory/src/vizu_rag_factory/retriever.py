"""Custom LangChain retriever backed by Supabase vector_db.

Calls the `search-documents` Edge Function to embed a query and
perform cosine-similarity search against ``vector_db.document_chunks``.
"""

import json
import logging

import httpx
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

logger = logging.getLogger(__name__)


class SupabaseVectorRetriever(BaseRetriever):
    """Retrieves documents from Supabase vector_db via the search-documents Edge Function."""

    supabase_url: str = Field(description="Supabase project URL")
    supabase_service_key: str = Field(description="Service role key for auth")
    client_id: str = Field(description="Client UUID for RLS filtering")
    match_count: int = Field(default=5)
    match_threshold: float = Field(default=0.5)

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
            f"{self.supabase_url}/functions/v1/search-documents",
            json={
                "query": query,
                "client_id": self.client_id,
                "match_count": self.match_count,
                "match_threshold": self.match_threshold,
            },
            headers={
                "Authorization": f"Bearer {self.supabase_service_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        logger.debug(
            f"[SupabaseVectorRetriever] Got {len(results)} results for client {self.client_id}"
        )

        return [
            Document(
                page_content=result["content"],
                metadata={
                    **(
                        json.loads(result["metadata"])
                        if isinstance(result.get("metadata"), str)
                        else (result.get("metadata") or {})
                    ),
                    "document_id": result["document_id"],
                    "similarity": result["similarity"],
                },
            )
            for result in results
        ]
