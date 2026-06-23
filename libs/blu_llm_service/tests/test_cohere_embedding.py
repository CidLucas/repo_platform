# libs/blu_llm_service/tests/test_cohere_embedding.py
"""Testes unitários do CohereEmbeddingClient (T3.1f — Seção 1).

Foco nos cenários específicos requeridos:
- embed_query com 384 dimensões
- Batching de documentos (200 → 3 batches)
- Lista vazia
- API key ausente → ValueError
- Erro HTTP 500 → exception
"""

from unittest.mock import MagicMock, patch

import pytest

from blu_llm_service.client import CohereEmbeddingClient, get_cohere_embedding_model
from blu_llm_service.config import get_llm_settings


class TestCohereEmbeddingClientUnit:
    """Testes unitários focados do CohereEmbeddingClient."""

    @pytest.fixture
    def client(self):
        return CohereEmbeddingClient(api_key="test-key")

    # ── 1. test_embed_query_returns_384_dims ──────────────────────

    @patch("requests.post")
    def test_embed_query_returns_384_dims(self, mock_post, client):
        """Mock API response, verificar que embed_query retorna 384 floats."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.1] * 384]}
        }
        mock_post.return_value = mock_response

        embedding = client.embed_query("alguma consulta")

        assert len(embedding) == 384, f"Esperado 384 dimensões, obtido {len(embedding)}"
        assert all(isinstance(v, float) for v in embedding), "Todos os valores devem ser float"
        assert embedding[0] == 0.1

        # Verifica input_type usado
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["input_type"] == "search_query"

    # ── 2. test_embed_documents_batching ──────────────────────────

    @patch("requests.post")
    def test_embed_documents_batching(self, mock_post, client):
        """200 textos → 3 batches (96 + 96 + 8)."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            batch_texts = kwargs["json"]["texts"]
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "embeddings": {"float": [[0.0] * 384 for _ in batch_texts]}
            }
            return mock_resp

        mock_post.side_effect = side_effect

        embeddings = client.embed_documents([f"doc {i}" for i in range(200)])

        assert len(embeddings) == 200
        assert call_count == 3, f"Esperado 3 batches, obtido {call_count}"

    # ── 3. test_embed_documents_empty_list ────────────────────────

    def test_embed_documents_empty_list(self, client):
        """Lista vazia retorna [] sem chamar API."""
        result = client.embed_documents([])
        assert result == []
        assert len(result) == 0

    # ── 4. test_missing_api_key_raises ────────────────────────────

    def test_missing_api_key_raises(self):
        """CO_API_KEY ausente → ValueError na factory function."""
        settings = get_llm_settings()
        old_key = settings.CO_API_KEY
        settings.CO_API_KEY = None
        try:
            with pytest.raises(ValueError, match="CO_API_KEY"):
                get_cohere_embedding_model()
        finally:
            settings.CO_API_KEY = old_key

    # ── 5. test_api_error_raises ──────────────────────────────────

    @patch("requests.post")
    def test_api_error_raises(self, mock_post, client):
        """HTTP 500 → exception propagada."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception(
            "500 Internal Server Error"
        )
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as excinfo:
            client.embed_documents(["teste"])

        assert "500" in str(excinfo.value)
