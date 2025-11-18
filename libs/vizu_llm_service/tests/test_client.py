# libs/vizu_llm_service/tests/unit/test_client.py

import pytest
from unittest.mock import patch, MagicMock
from langchain_community.chat_models import ChatOllama
from vizu_llm_service.client import (
    VizuEmbeddingAPIClient,
    get_embedding_model,
    get_model,
    ModelTier
)
from vizu_llm_service.config import get_llm_settings

# --- Testes do Cliente de Embedding (VizuEmbeddingAPIClient) ---

class TestVizuEmbeddingAPIClient:

    @pytest.fixture
    def client(self):
        return VizuEmbeddingAPIClient(base_url="http://test-service:11435")

    @patch("vizu_llm_service.client.requests.post")
    def test_embed_documents_success(self, mock_post, client):
        """Testa se o cliente envia o payload correto e processa a resposta."""
        # Configura o mock para retornar sucesso
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simula a resposta da API: lista de vetores
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
        mock_post.return_value = mock_response

        texts = ["texto 1", "texto 2"]
        embeddings = client.embed_documents(texts)

        # Verificações
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]

        # Verifica se a chamada HTTP foi feita corretamente
        mock_post.assert_called_once_with(
            "http://test-service:11435/embed",
            json={"texts": texts},
            timeout=30
        )

    @patch("vizu_llm_service.client.requests.post")
    def test_embed_query_success(self, mock_post, client):
        """Testa a vetorização de uma única query."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # A API sempre retorna lista de listas, mesmo para um item
        mock_response.json.return_value = {"embeddings": [[0.9, 0.8, 0.7]]}
        mock_post.return_value = mock_response

        text = "minha query"
        embedding = client.embed_query(text)

        # Deve retornar uma lista simples (float list), não lista de listas
        assert embedding == [0.9, 0.8, 0.7]

        # Verifica se enviou como lista na API
        mock_post.assert_called_once()
        assert mock_post.call_args[1]['json']['texts'] == ["minha query"]

    @patch("vizu_llm_service.client.requests.post")
    def test_api_failure(self, mock_post, client):
        """Testa se o cliente lança exceção quando a API falha."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Erro 500 do Servidor")
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as excinfo:
            client.embed_documents(["teste"])

        assert "Erro 500" in str(excinfo.value)

# --- Testes das Factories (get_model / get_embedding_model) ---

def test_get_embedding_model_factory():
    """Verifica se a factory retorna nosso cliente customizado com a URL certa."""
    # Força a configuração para o teste
    settings = get_llm_settings()
    settings.EMBEDDING_SERVICE_URL = "http://config-url:1234"

    model = get_embedding_model()

    assert isinstance(model, VizuEmbeddingAPIClient)
    assert model.api_url == "http://config-url:1234/embed"

def test_get_model_factory():
    """Verifica se a factory retorna o ChatOllama configurado corretamente."""
    settings = get_llm_settings()
    settings.OLLAMA_BASE_URL = "http://ollama-test:11434"

    # Teste com Tier Default
    llm = get_model(tier=ModelTier.DEFAULT)

    assert isinstance(llm, ChatOllama)
    assert llm.base_url == "http://ollama-test:11434"
    assert llm.model == "llama3.2:latest" # Conforme definimos no client.py revisado

def test_get_model_tier_mapping():
    """Verifica se a troca de Tier altera o modelo."""
    llm_fast = get_model(tier=ModelTier.FAST)
    # No código revisado, mapeamos FAST para 'phi3:mini'
    assert llm_fast.model == "phi3:mini"