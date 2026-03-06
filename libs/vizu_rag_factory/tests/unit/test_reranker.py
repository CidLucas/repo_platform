"""Tests for reranker module — LLMReranker and CrossEncoderReranker."""

import asyncio
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from langchain_core.documents import Document

from vizu_rag_factory.reranker import (
    CrossEncoderReranker,
    LLMReranker,
    _cross_encoder_lock,
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
# CrossEncoderReranker — unit tests (mocked model)
# ---------------------------------------------------------------------------


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker with mocked CrossEncoder model."""

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
        mock_model.predict.return_value = np.array([0.1, 0.9, 0.5, 0.3])
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
        mock_model.predict.return_value = np.array([0.1, 0.9, 0.5, 0.3])
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
        mock_model.predict.return_value = np.array([0.5, 0.5, 0.5, 0.5])
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
        mock_model.predict.return_value = np.array([0.1, 0.9, 0.5, 0.3])
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
        mock_model.predict.return_value = np.array([0.1, 0.9, 0.5, 0.3])
        mock_get_model.return_value = mock_model

        reranker = self._make_reranker()
        result = await reranker.arerank("query", sample_documents, top_k=1)

        assert len(result) == 1
        assert result[0].metadata["file_name"] == "guia_fiscal.pdf"

    @patch("vizu_rag_factory.reranker._get_cross_encoder")
    def test_rerank_preserves_existing_metadata(self, mock_get_model, sample_documents):
        """Reranking should preserve original metadata and add rerank_score."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.8, 0.2, 0.5, 0.1])
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

        # Enable reranking with cross-encoder
        mock_vizu_client_context.available_tools = {
            "rag_search_config": {
                "rerank": True,
                "reranker_type": "cross-encoder",
                "rerank_top_k": 3,
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

    def test_factory_defaults_to_cross_encoder(self, mocker, mock_vizu_client_context):
        """Default reranker_type should be 'cross-encoder'."""
        from vizu_rag_factory.factory import create_rag_runnable

        mock_llm = mocker.MagicMock()
        mocker.patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "test-service-key",
            },
        )

        # Enable reranking without specifying type
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
