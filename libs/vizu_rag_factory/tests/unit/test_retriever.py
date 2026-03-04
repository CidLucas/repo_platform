"""Tests for SupabaseVectorRetriever."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from langchain_core.documents import Document

from vizu_rag_factory.retriever import SupabaseVectorRetriever


@pytest.fixture
def retriever() -> SupabaseVectorRetriever:
    return SupabaseVectorRetriever(
        supabase_url="https://test.supabase.co",
        supabase_service_key="test-service-key",
        client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        match_count=3,
        match_threshold=0.6,
    )


def test_retriever_returns_documents(retriever: SupabaseVectorRetriever):
    """Test that the retriever correctly parses Edge Function response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "results": [
            {
                "content": "Chunk text 1",
                "document_id": "doc-uuid-1",
                "similarity": 0.92,
                "metadata": {"source_file": "manual.pdf", "page": 3},
            },
            {
                "content": "Chunk text 2",
                "document_id": "doc-uuid-2",
                "similarity": 0.85,
                "metadata": None,
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response) as mock_post:
        docs = retriever.invoke("What is the return policy?")

    assert len(docs) == 2
    assert isinstance(docs[0], Document)
    assert docs[0].page_content == "Chunk text 1"
    assert docs[0].metadata["document_id"] == "doc-uuid-1"
    assert docs[0].metadata["similarity"] == 0.92
    assert docs[0].metadata["source_file"] == "manual.pdf"

    # Second doc with None metadata should still work
    assert docs[1].metadata["document_id"] == "doc-uuid-2"

    # Verify the request was formed correctly
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["client_id"] == retriever.client_id
    assert call_kwargs.kwargs["json"]["match_count"] == 3
    assert call_kwargs.kwargs["json"]["match_threshold"] == 0.6


def test_retriever_empty_results(retriever: SupabaseVectorRetriever):
    """Test that the retriever handles empty results."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response):
        docs = retriever.invoke("nonexistent query")

    assert docs == []


def test_retriever_raises_on_http_error(retriever: SupabaseVectorRetriever):
    """Test that HTTP errors are propagated."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            retriever.invoke("will fail")
