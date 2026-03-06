"""Tests for SupabaseVectorRetriever and HybridRetriever."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.documents import Document

from vizu_rag_factory.retriever import HybridRetriever, SupabaseVectorRetriever

# ── Fixtures ─────────────────────────────────────────


@pytest.fixture
def retriever() -> SupabaseVectorRetriever:
    return SupabaseVectorRetriever(
        supabase_url="https://test.supabase.co",
        supabase_service_key="test-service-key",
        client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        match_count=3,
        match_threshold=0.6,
    )


@pytest.fixture
def hybrid_retriever() -> HybridRetriever:
    return HybridRetriever(
        supabase_url="https://test.supabase.co",
        supabase_service_key="test-service-key",
        client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        match_count=5,
        match_threshold=0.4,
        search_mode="hybrid",
        fusion_strategy="rrf",
        keyword_weight=0.4,
        vector_weight=0.6,
        scope=["platform", "client"],
    )


def _mock_response(results: list[dict]) -> MagicMock:
    """Helper to build a mock httpx.Response."""
    mock = MagicMock(spec=httpx.Response)
    mock.json.return_value = {"results": results}
    mock.raise_for_status = MagicMock()
    return mock


# ── SupabaseVectorRetriever Tests ────────────────────


def test_retriever_returns_documents(retriever: SupabaseVectorRetriever):
    """Test that the retriever correctly parses Edge Function response."""
    mock_response = _mock_response(
        [
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
    )

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
    mock_response = _mock_response([])

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


# ── HybridRetriever Tests ───────────────────────────


def test_hybrid_payload_contains_fusion_params(hybrid_retriever: HybridRetriever):
    """Test that the hybrid retriever sends all fusion parameters in the payload."""
    mock_response = _mock_response([])

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response) as mock_post:
        hybrid_retriever.invoke("revenue by quarter")

    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["search_mode"] == "hybrid"
    assert payload["fusion_strategy"] == "rrf"
    assert payload["keyword_weight"] == 0.4
    assert payload["vector_weight"] == 0.6
    assert payload["scope"] == ["platform", "client"]
    assert payload["match_count"] == 5
    assert payload["match_threshold"] == 0.4


def test_hybrid_returns_documents_with_keyword_score(hybrid_retriever: HybridRetriever):
    """Test that hybrid results include keyword_score and combined_score metadata."""
    mock_response = _mock_response(
        [
            {
                "content": "Revenue data Q1",
                "document_id": "doc-uuid-1",
                "similarity": 0.88,
                "keyword_score": 0.72,
                "combined_score": 0.82,
                "scope": "client",
                "category": "dados_negocio",
                "metadata": {"page": 1},
            },
        ]
    )

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response):
        docs = hybrid_retriever.invoke("revenue")

    assert len(docs) == 1
    assert docs[0].page_content == "Revenue data Q1"
    assert docs[0].metadata["keyword_score"] == 0.72
    assert docs[0].metadata["combined_score"] == 0.82
    assert docs[0].metadata["scope"] == "client"
    assert docs[0].metadata["category"] == "dados_negocio"


def test_hybrid_categories_filter(hybrid_retriever: HybridRetriever):
    """Test that categories are included in the payload when set."""
    hybrid_retriever.categories = ["tax_knowledge", "dados_negocio"]
    mock_response = _mock_response([])

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response) as mock_post:
        hybrid_retriever.invoke("IRPJ")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["categories"] == ["tax_knowledge", "dados_negocio"]


def test_hybrid_document_ids_filter(hybrid_retriever: HybridRetriever):
    """Test that document_ids are included in the payload when set."""
    hybrid_retriever.document_ids = ["doc-1", "doc-2"]
    mock_response = _mock_response([])

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response) as mock_post:
        hybrid_retriever.invoke("search within specific docs")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["document_ids"] == ["doc-1", "doc-2"]


@pytest.mark.asyncio
async def test_hybrid_async_retrieval(hybrid_retriever: HybridRetriever):
    """Test that HybridRetriever works asynchronously."""
    mock_response = _mock_response(
        [
            {
                "content": "Async result",
                "document_id": "doc-uuid-async",
                "similarity": 0.90,
                "keyword_score": 0.65,
                "combined_score": 0.80,
                "metadata": {},
            },
        ]
    )

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("vizu_rag_factory.retriever.httpx.AsyncClient", return_value=mock_client):
        docs = await hybrid_retriever.ainvoke("async query")

    assert len(docs) == 1
    assert docs[0].page_content == "Async result"
    assert docs[0].metadata["combined_score"] == 0.80


def test_hybrid_empty_results(hybrid_retriever: HybridRetriever):
    """Test that the hybrid retriever handles empty results."""
    mock_response = _mock_response([])

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response):
        docs = hybrid_retriever.invoke("nonexistent")

    assert docs == []


def test_hybrid_raises_on_http_error(hybrid_retriever: HybridRetriever):
    """Test that HTTP errors are propagated by the hybrid retriever."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch("vizu_rag_factory.retriever.httpx.post", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            hybrid_retriever.invoke("will fail")
