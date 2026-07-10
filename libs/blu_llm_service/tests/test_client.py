# libs/blu_llm_service/tests/unit/test_client.py

from unittest.mock import MagicMock, patch

import pytest
from langchain_community.chat_models import ChatOllama

from blu_llm_service.client import (
    BluEmbeddingAPIClient,
    CohereEmbeddingClient,
    LLMProvider,
    ModelTier,
    get_cohere_embedding_model,
    get_embedding_model,
    get_model,
)
from blu_llm_service.config import get_llm_settings

# --- Testes do Cliente de Embedding (BluEmbeddingAPIClient) ---


class TestBluEmbeddingAPIClient:
    @pytest.fixture
    def client(self):
        return BluEmbeddingAPIClient(base_url="http://test-service:11435")

    @patch("blu_llm_service.client.requests.post")
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
            "http://test-service:11435/embed", json={"texts": texts}, timeout=30
        )

    @patch("blu_llm_service.client.requests.post")
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
        assert mock_post.call_args[1]["json"]["texts"] == ["minha query"]

    @patch("blu_llm_service.client.requests.post")
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

    assert isinstance(model, BluEmbeddingAPIClient)
    assert model.api_url == "http://config-url:1234/embed"


def test_get_model_factory():
    """Verifica se a factory retorna o ChatOllama configurado para Ollama Cloud."""
    settings = get_llm_settings()
    settings.OLLAMA_CLOUD_API_KEY = "test-api-key"
    settings.OLLAMA_CLOUD_BASE_URL = "https://ollama.com"

    # Teste com Tier Default (Ollama Cloud)
    llm = get_model(tier=ModelTier.DEFAULT)

    assert isinstance(llm, ChatOllama)
    assert llm.base_url == "https://ollama.com"
    assert llm.model == "gpt-oss:20b"  # Default model for Ollama Cloud


def test_get_model_tier_mapping():
    """Verifica se a troca de Tier altera o modelo."""
    settings = get_llm_settings()
    settings.OLLAMA_CLOUD_API_KEY = "test-api-key"

    llm_powerful = get_model(tier=ModelTier.POWERFUL)
    # POWERFUL maps to deepseek-v4-pro for Ollama Cloud
    assert llm_powerful.bound.model == "deepseek-v4-pro"


# --- Testes do Provider DeepSeek ---


class TestDeepSeekProvider:
    def test_factory_returns_chatopenai_with_deepseek_base_url(self):
        """DeepSeek usa ChatOpenAI apontando para api.deepseek.com."""
        from langchain_openai import ChatOpenAI

        settings = get_llm_settings()
        settings.DEEPSEEK_API_KEY = "test-deepseek-key"

        llm = get_model(provider=LLMProvider.DEEPSEEK, tier=ModelTier.DEFAULT)

        assert isinstance(llm, ChatOpenAI)
        assert llm.openai_api_base == "https://api.deepseek.com"
        assert llm.model_name == "deepseek-v4-flash"

    def test_tier_powerful_uses_v4_pro(self):
        """Tier POWERFUL mapeia para deepseek-v4-pro."""
        settings = get_llm_settings()
        settings.DEEPSEEK_API_KEY = "test-deepseek-key"

        llm = get_model(provider=LLMProvider.DEEPSEEK, tier=ModelTier.POWERFUL)

        assert llm.model_name == "deepseek-v4-pro"

    def test_missing_api_key_raises(self):
        """Sem DEEPSEEK_API_KEY, a factory falha com mensagem clara."""
        settings = get_llm_settings()
        settings.DEEPSEEK_API_KEY = None

        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            get_model(provider=LLMProvider.DEEPSEEK)


# --- Testes do Cliente de Embedding Cohere (CohereEmbeddingClient) ---


class TestCohereEmbeddingClient:
    @pytest.fixture
    def client(self):
        return CohereEmbeddingClient(api_key="test-cohere-api-key")

    @patch("blu_llm_service.client.requests.post")
    def test_embed_documents_success(self, mock_post, client):
        """Testa embed_documents com batching e input_type='search_document'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.1] * 384, [0.2] * 384]}
        }
        mock_post.return_value = mock_response

        texts = ["documento 1", "documento 2"]
        embeddings = client.embed_documents(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384
        assert len(embeddings[1]) == 384

        # Verifica chamada HTTP
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.cohere.com/v2/embed"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-cohere-api-key"
        assert call_args[1]["json"]["input_type"] == "search_document"
        assert call_args[1]["json"]["texts"] == texts

    @patch("blu_llm_service.client.requests.post")
    def test_embed_query_success(self, mock_post, client):
        """Testa embed_query com input_type='search_query'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.9] * 384]}
        }
        mock_post.return_value = mock_response

        embedding = client.embed_query("minha query")

        assert len(embedding) == 384
        assert embedding[0] == 0.9

        # Verifica input_type='search_query'
        call_args = mock_post.call_args
        assert call_args[1]["json"]["input_type"] == "search_query"

    @patch("blu_llm_service.client.requests.post")
    def test_batching_above_96(self, mock_post, client):
        """Testa que textos acima de BATCH_SIZE (96) são divididos em batches."""
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

        total_texts = 200  # 2 batches: 96 + 104 → wait, should be 96 + 96 + 8 = 3 batches
        # Actually: 200 / 96 = 3 batches (96, 96, 8)
        embeddings = client.embed_documents([f"texto {i}" for i in range(total_texts)])

        assert len(embeddings) == 200
        assert call_count == 3  # ceil(200/96) = 3

    @patch("blu_llm_service.client.requests.post")
    def test_batching_exact_96(self, mock_post, client):
        """Testa que exatamente 96 textos fazem 1 chamada."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.0] * 384 for _ in range(96)]}
        }
        mock_post.return_value = mock_response

        embeddings = client.embed_documents([f"texto {i}" for i in range(96)])

        assert len(embeddings) == 96
        assert mock_post.call_count == 1

    @patch("blu_llm_service.client.requests.post")
    def test_api_error(self, mock_post, client):
        """Testa que erro HTTP da Cohere é propagado."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as excinfo:
            client.embed_documents(["teste"])

        assert "401" in str(excinfo.value)


# --- Testes da Factory Function (get_cohere_embedding_model) ---


class TestGetCohereEmbeddingModel:
    def test_uses_settings_api_key(self):
        """Testa que CO_API_KEY do settings é usada."""
        settings = get_llm_settings()
        settings.CO_API_KEY = "settings-key-test"
        try:
            model = get_cohere_embedding_model()
            assert isinstance(model, CohereEmbeddingClient)
            assert model.api_key == "settings-key-test"
        finally:
            settings.CO_API_KEY = None

    @patch.dict("os.environ", {"CO_API_KEY": "env-key-test"}, clear=True)
    def test_falls_back_to_env(self):
        """Testa fallback para CO_API_KEY do ambiente."""
        settings = get_llm_settings()
        settings.CO_API_KEY = None
        try:
            model = get_cohere_embedding_model()
            assert isinstance(model, CohereEmbeddingClient)
            assert model.api_key == "env-key-test"
        finally:
            settings.CO_API_KEY = None

    def test_missing_api_key_raises(self):
        """Testa que ValueError é lançado sem CO_API_KEY."""
        settings = get_llm_settings()
        old_key = settings.CO_API_KEY
        settings.CO_API_KEY = None
        try:
            with pytest.raises(ValueError, match="CO_API_KEY não configurada"):
                get_cohere_embedding_model()
        finally:
            settings.CO_API_KEY = old_key
