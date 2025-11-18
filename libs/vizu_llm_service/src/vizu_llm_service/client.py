# libs/vizu_llm_service/src/vizu_llm_service/client.py

import requests
from typing import List, Optional
from enum import Enum

from langchain_community.chat_models import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.embeddings import Embeddings
from langfuse.langchain import CallbackHandler

from .config import get_llm_settings, LLMSettings

# --- REMOVIDO: Imports pesados ---
# from langchain_huggingface import HuggingFaceEmbeddings  <-- ISSO CAUSA O PESO

class ModelTier(str, Enum):
    """Mantido para compatibilidade com seu código existente"""
    DEFAULT = "default"
    FAST = "fast"
    POWERFUL = "powerful"

class ModelTask(str, Enum):
    """Mantido para compatibilidade"""
    GENERAL_AGENT = "general_agent"
    CLASSIFICATION = "classification"


# --- NOVO: Cliente Leve de Embedding ---
class VizuEmbeddingAPIClient(Embeddings):
    """
    Cliente que substitui o HuggingFaceEmbeddings.
    Em vez de carregar o modelo na RAM, ele faz um POST para o embedding_service.
    """
    def __init__(self, base_url: str):
        self.api_url = f"{base_url.rstrip('/')}/embed"

    def _call_api(self, texts: List[str]) -> List[List[float]]:
        try:
            response = requests.post(
                self.api_url,
                json={"texts": texts},
                timeout=30
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except Exception as e:
            print(f"ERRO: Falha ao conectar ao Embedding Service ({self.api_url}): {e}")
            raise e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._call_api(texts)

    def embed_query(self, text: str) -> List[float]:
        # A API espera uma lista, então enviamos [text] e pegamos o primeiro resultado
        return self._call_api([text])[0]


# --- Helpers de Callback (Mantidos) ---
def _get_langfuse_callback(settings: LLMSettings) -> Optional[CallbackHandler]:
    if not settings.langfuse_enabled:
        return None
    return CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST
    )

def _get_base_callbacks(settings: LLMSettings) -> List[BaseCallbackHandler]:
    callbacks = []
    lf = _get_langfuse_callback(settings)
    if lf:
        callbacks.append(lf)
    return callbacks


# --- Fábricas Principais ---

def get_model(
    tier: ModelTier = ModelTier.DEFAULT,
    task: ModelTask = ModelTask.GENERAL_AGENT
) -> BaseChatModel:
    """
    Retorna o cliente do ChatOllama.
    """
    settings = get_llm_settings()
    callbacks = _get_base_callbacks(settings)

    # Mapeamento simplificado para o modelo padrão
    model_name = "llama3.2:latest"
    if tier == ModelTier.FAST:
        model_name = "phi3:mini" # Exemplo

    print(f"INFO: Conectando ao Ollama em {settings.OLLAMA_BASE_URL} modelo={model_name}")

    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model_name,
        callbacks=callbacks
    )

def get_embedding_model() -> Embeddings:
    """
    Retorna o cliente de API leve.
    NÃO carrega mais modelos pesados localmente.
    """
    settings = get_llm_settings()
    print(f"INFO: Inicializando VizuEmbeddingAPIClient apontando para {settings.EMBEDDING_SERVICE_URL}")

    return VizuEmbeddingAPIClient(base_url=settings.EMBEDDING_SERVICE_URL)