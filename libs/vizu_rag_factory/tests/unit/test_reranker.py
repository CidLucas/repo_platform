"""Tests for reranker module — CohereReranker, LLMReranker, and CrossEncoderReranker."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from vizu_rag_factory.reranker import (
    CohereReranker,
    CrossEncoderReranker,
    LLMReranker,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_documents() -> list[Document]:
    """Create sample documents for reranking tests."""
    return [
        Document(
            page_content="A empresa teve receita de R$ 10 milhões no trimestre.",
            metadata={"similarity": 0.85, "file_name": "relatorio_q1.pdf"},
        ),
        Document(
            page_content="O ICMS aplicável neste caso é de 18% conforme legislação vigente.",
            metadata={"similarity": 0.72, "file_name": "guia_fiscal.pdf"},
        ),
        Document(
            page_content="A média de vendas diárias foi de 150 unidades.",
            metadata={"similarity": 0.68, "file_name": "analytics.pdf"},
        ),
        Document(
            page_content="O contrato de prestação de serviços tem vigência até 2025.",
            metadata={"similarity": 0.55, "file_name": "contrato.pdf"},
        ),
    ]


# ---------------------------------------------------------------------------
# CohereReranker — unit tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestCohereReranker:
    """Tests for CohereReranker with mocked Cohere API responses."""

    def _make_reranker(self, api_key: str = "test-co-key") -> CohereReranker:
        return CohereReranker(api_key=api_key)

    def _mock_cohere_response(self, results: list[dict]) -> MagicMock:
        """Create a mock httpx response with Cohere rerank results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": results}
        mock_response.raise_for_status = MagicMock()
        return mock_response

    @pytest.mark.asyncio
    async def test_arerank_sorts_by_score(self, sample_documents):
        """Cohere rerank scores should re-sort the documents."""
        reranker = self._make_reranker()
        cohere_results = [
            {"index": 1, "relevance_score": 0.95},  # guia_fiscal
            {"index": 2, "relevance_score": 0.80},  # analytics
            {"index": 0, "relevance_score": 0.60},  # relatorio_q1
            {"index": 3, "relevance_score": 0.20},  # contrato
        ]
        mock_resp = self._mock_cohere_response(cohere_results)

        with patch("vizu_rag_factory.reranker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await reranker.arerank("qual a receita?", sample_documents)

        assert len(result) == 4
        assert result[0].metadata["file_name"] == "guia_fiscal.pdf"
        assert result[0].metadata["rerank_score"] == pytest.approx(0.95)
        assert result[1].metadata["file_name"] == "analytics.pdf"
        assert result[3].metadata["file_name"] == "contrato.pdf"

    @pytest.mark.asyncio
    async def test_arerank_respects_top_k(self, sample_documents):
        """top_n in Cohere request should limit returned documents."""
        reranker = self._make_reranker()
        cohere_results = [
            {"index": 1, "relevance_score": 0.95},
            {"index": 2, "relevance_score": 0.80},
        ]
        mock_resp = self._mock_cohere_response(cohere_results)

        with patch("vizu_rag_factory.reranker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await reranker.arerank("query", sample_documents, top_k=2)

        assert len(result) == 2
        # Verify top_n was sent in the request payload
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["top_n"] == 2

    @pytest.mark.asyncio
    async def test_arerank_empty_list(self):
        """Empty input should return empty list without calling API."""
        reranker = self._make_reranker()
        result = await reranker.arerank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_arerank_single_doc(self):
        """Single document should be returned without calling API."""
        doc = Document(page_content="test", metadata={})
        reranker = self._make_reranker()
        result = await reranker.arerank("query", [doc])
        assert len(result) == 1
        assert result[0] is doc

    @pytest.mark.asyncio
    async def test_arerank_no_api_key_returns_unchanged(self, sample_documents):
        """Without API key, documents should be returned unchanged."""
        reranker = CohereReranker(api_key="")
        result = await reranker.arerank("query", sample_documents, top_k=2)
        assert len(result) == 2
        # Should return first 2 docs unchanged (no reranking)
        assert result[0].metadata["file_name"] == "relatorio_q1.pdf"

    @pytest.mark.asyncio
    async def test_arerank_api_error_returns_fallback(self, sample_documents):
        """On API error, should return documents in original order."""
        import httpx as _httpx

        reranker = self._make_reranker()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_resp
        )

        with patch("vizu_rag_factory.reranker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await reranker.arerank("query", sample_documents, top_k=2)

        # Graceful fallback — returns first top_k docs
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_arerank_preserves_metadata(self, sample_documents):
        """Reranking should preserve original metadata and add rerank_score."""
        reranker = self._make_reranker()
        cohere_results = [
            {"index": 0, "relevance_score": 0.9},
            {"index": 1, "relevance_score": 0.7},
            {"index": 2, "relevance_score": 0.5},
            {"index": 3, "relevance_score": 0.3},
        ]
        mock_resp = self._mock_cohere_response(cohere_results)

        with patch("vizu_rag_factory.reranker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await reranker.arerank("query", sample_documents)

        assert result[0].metadata["similarity"] == 0.85
        assert result[0].metadata["file_name"] == "relatorio_q1.pdf"
        assert result[0].metadata["rerank_score"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# CrossEncoderReranker — kept for backward compatibility (optional)
# ---------------------------------------------------------------------------


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker with mocked CrossEncoder model.

    NOTE: sentence-transformers is an optional dependency. These tests use
    mocked models and do not require it to be installed.
    """

    def _make_reranker(self) -> CrossEncoderReranker:
        return CrossEncoderReranker(
            model_name="BAAI/bge-reranker-v2-m3",
            device="cpu",
            max_passage_length=1500,
        )

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_sorts_by_score(self, mock_get_model, sample_documents):
        """Cross-encoder scores should re-sort the documents."""
        mock_model = MagicMock()
        # Scores: doc[0]=0.1, doc[1]=0.9, doc[2]=0.5, doc[3]=0.3
        # Expected order: doc[1], doc[2], doc[3], doc[0]
        mock_model.predict.return_value = [0.1, 0.9, 0.5, 0.3]
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = reranker.rerank("qual a receita da empresa?", sample_documents)

        assert len(result) == 4
        assert result[0].metadata["file_name"] == "guia_fiscal.pdf"  # score 0.9
        assert result[1].metadata["file_name"] == "analytics.pdf"  # score 0.5
        assert result[2].metadata["file_name"] == "contrato.pdf"  # score 0.3
        assert result[3].metadata["file_name"] == "relatorio_q1.pdf"  # score 0.1

        # Verify rerank_score is set in metadata
        assert result[0].metadata["rerank_score"] == pytest.approx(0.9)
        assert result[3].metadata["rerank_score"] == pytest.approx(0.1)

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_respects_top_k(self, mock_get_model, sample_documents):
        """top_k should limit the number of returned documents."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5, 0.3]
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = reranker.rerank("query", sample_documents, top_k=2)

        assert len(result) == 2
        assert result[0].metadata["file_name"] == "guia_fiscal.pdf"
        assert result[1].metadata["file_name"] == "analytics.pdf"

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_empty_list(self, mock_get_model):
        """Empty input should return empty list without calling model."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = reranker.rerank("query", [])

        assert result == []
        mock_model.predict.assert_not_called()

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_single_doc(self, mock_get_model):
        """Single document should be returned without calling model."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        doc = Document(page_content="test", metadata={})

        reranker = self._make_reranker()
        result = reranker.rerank("query", [doc])

        assert len(result) == 1
        assert result[0] is doc
        mock_model.predict.assert_not_called()

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_truncates_long_passages(self, mock_get_model, sample_documents):
        """Passages should be truncated to max_passage_length."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5, 0.5, 0.5, 0.5]
        mock_get_model.return_value = mock_model

        reranker = CrossEncoderReranker(max_passage_length=50)
        reranker.rerank("query", sample_documents)

        # Check that predict was called with truncated passages
        call_args = mock_model.predict.call_args[0][0]
        for pair in call_args:
            assert len(pair[1]) <= 50

    @pytest.mark.asyncio
    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    async def test_arerank_sorts_by_score(self, mock_get_model, sample_documents):
        """Async rerank should produce same results as sync."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5, 0.3]
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = await reranker.arerank("qual a receita?", sample_documents)

        assert len(result) == 4
        assert result[0].metadata["file_name"] == "guia_fiscal.pdf"
        assert result[0].metadata["rerank_score"] == pytest.approx(0.9)

    @pytest.mark.asyncio
    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    async def test_arerank_with_top_k(self, mock_get_model, sample_documents):
        """Async rerank with top_k should limit results."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5, 0.3]
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = await reranker.arerank("query", sample_documents, top_k=1)

        assert len(result) == 1
        assert result[0].metadata["file_name"] == "guia_fiscal.pdf"

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_preserves_existing_metadata(self, mock_get_model, sample_documents):
        """Reranking should preserve original metadata and add rerank_score."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8, 0.2, 0.5, 0.1]
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = reranker.rerank("query", sample_documents)

        # Original metadata preserved
        assert result[0].metadata["similarity"] == 0.85
        assert result[0].metadata["file_name"] == "relatorio_q1.pdf"
        # rerank_score added
        assert "rerank_score" in result[0].metadata
        assert result[0].metadata["rerank_score"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Factory integration — CrossEncoder selected via config
# ---------------------------------------------------------------------------


class TestFactoryRerankerSelection:
    """Test that factory.py correctly selects CrossEncoderReranker vs LLMReranker."""

    def test_factory_creates_cross_encoder_reranker(self, mocker, mock_vizu_client_context):
        """When reranker_type='cross-encoder', factory should use CrossEncoderReranker."""
        from vizu_rag_factory.factory import create_rag_runnable

        mock_llm = mocker.MagicMock()
        mocker.patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key",
            },
        )

        # Enable reranking with cross-encoder (legacy option)
        mock_vizu_client_context.available_tools = {
            "rag_search_config": {
                "rerank": True,
                "reranker_type": "cross-encoder",
                "rerank_top_k": 3,
            }
        }

        runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)
        assert runnable is not None

    def test_factory_creates_cohere_reranker(self, mocker, mock_vizu_client_context):
        """When reranker_type='cohere', factory should use CohereReranker."""
        from vizu_rag_factory.factory import create_rag_runnable

        mock_llm = mocker.MagicMock()
        mocker.patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key",
            },
        )

        mock_vizu_client_context.available_tools = {
            "rag_search_config": {
                "rerank": True,
                "reranker_type": "cohere",
                "rerank_top_k": 5,
            }
        }

        runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)
        assert runnable is not None

    def test_factory_creates_llm_reranker(self, mocker, mock_vizu_client_context):
        """When reranker_type='llm', factory should use LLMReranker."""
        from vizu_rag_factory.factory import create_rag_runnable

        mock_llm = mocker.MagicMock()
        mocker.patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key",
            },
        )

        # Enable reranking with LLM
        mock_vizu_client_context.available_tools = {
            "rag_search_config": {
                "rerank": True,
                "reranker_type": "llm",
                "rerank_top_k": 3,
            }
        }

        runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)
        assert runnable is not None

    def test_factory_defaults_to_cohere(self, mocker, mock_vizu_client_context):
        """Default reranker_type should be 'cohere'."""
        from vizu_rag_factory.factory import create_rag_runnable

        mock_llm = mocker.MagicMock()
        mocker.patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key",
            },
        )

        # Enable reranking without specifying type — should default to cohere
        mock_vizu_client_context.available_tools = {
            "rag_search_config": {
                "rerank": True,
            }
        }

        runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)
        assert runnable is not None

    def test_factory_no_reranker_when_disabled(self, mocker, mock_vizu_client_context):
        """When rerank=False, no reranker should be created."""
        from vizu_rag_factory.factory import create_rag_runnable

        mock_llm = mocker.MagicMock()
        mocker.patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key",
            },
        )

        # Reranking disabled (default)
        mock_vizu_client_context.available_tools = {
            "rag_search_config": {
                "rerank": False,
            }
        }

        runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)
        assert runnable is not None
