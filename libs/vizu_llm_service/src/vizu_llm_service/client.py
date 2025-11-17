# libs/vizu_llm_service/src/vizu_llm_service/client.py

import requests
from .config import get_llm_settings, LLMSettings
from langchain_community.chat_models import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks.base import BaseCallbackHandler
from typing import List, Optional

# --- INÍCIO: Imports de Embeddings ---
from langchain_core.embeddings import Embeddings
# --- REMOVIDO: Import local do HuggingFace ---
# from langchain_huggingface import HuggingFaceEmbeddings
# --- FIM: Imports de Embeddings ---

# --- INÍCIO: Imports do Langfuse ---
from langfuse.langchain import CallbackHandler
# --- FIM: Imports do Langfuse ---


# --- REMOVIDO: Classes de complexidade desnecessária ---
# class ModelTier(str, Enum): ...
# class ModelTask(str, Enum): ...


# --- INÍCIO: Nova Classe de Cliente de Embedding ---

class VizuEmbeddingAPIClient(Embeddings):
    """
    Cliente LangChain customizado para se conectar ao nosso
    microserviço de embedding interno.
    """
    def __init__(self, base_url: str, timeout: int = 60):
        if not base_url:
            raise ValueError("A URL base do serviço de embedding não pode ser nula.")
        self.base_url = base_url.rstrip('/')
        self.embed_url = f"{self.base_url}/embed"
        self.timeout = timeout

    def _call_api(self, texts: List[str]) -> List[List[float]]:
        """Função helper para chamar a API interna."""
        try:
            response = requests.post(
                self.embed_url,
                json={"texts": texts},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status() # Lança exceção para status 4xx/5xx
            data = response.json()

            if "embeddings" not in data or len(data["embeddings"]) != len(texts):
                raise ValueError("Resposta da API de embedding mal formatada.")

            return data["embeddings"]

        except requests.exceptions.ConnectionError as e:
            print(f"ERRO: Não foi possível conectar ao serviço de embedding em {self.base_url}.")
            raise ConnectionError(
                f"Serviço de embedding indisponível em {self.base_url}"
            ) from e
        except requests.exceptions.RequestException as e:
            print(f"ERRO: Falha ao chamar API de embedding: {e}")
            # Propaga a exceção para que o serviço consumidor saiba que falhou
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Vetoriza uma lista de documentos."""
        if not texts:
            return []
        print(f"INFO: Vetorizando {len(texts)} documentos via API de embedding...")
        return self._call_api(texts)

    def embed_query(self, text: str) -> List[float]:
        """Vetoriza uma única query."""
        print("INFO: Vetorizando query via API de embedding...")
        result = self._call_api([text])
        return result[0]

# --- FIM: Nova Classe de Cliente de Embedding ---


def _get_langfuse_callback(settings: LLMSettings) -> Optional[CallbackHandler]:
    """
    Função helper para inicializar o handler do Langfuse.
    (Sem alterações)
    """
    if not settings.langfuse_enabled:
        print("INFO: Langfuse não configurado. Pulando a inicialização do callback.")
        return None

    try:
        handler = CallbackHandler()
        print(f"INFO: LangfuseCallbackHandler inicializado para {settings.LANGFUSE_HOST}")
        return handler
    except Exception as e:
        print(f"AVISO: Falha ao inicializar o LangfuseCallbackHandler: {e}")
        return None

def _get_base_callbacks(settings: LLMSettings) -> List[BaseCallbackHandler]:
    """ Retorna a lista de callbacks base (incluindo Langfuse) (Sem alterações) """
    callbacks: List[BaseCallbackHandler] = []
    langfuse_handler = _get_langfuse_callback(settings)
    if langfuse_handler:
        callbacks.append(langfuse_handler)
    return callbacks

def get_model() -> BaseChatModel:
    """
    Conecta-se ao Ollama e retorna o modelo de chat padrão da Vizu.

    Simplificado para usar o modelo customizado provisionado pelo
    nosso 'ollama_service'.
    """
    settings = get_llm_settings()
    callbacks = _get_base_callbacks(settings)

    # --- ALTERAÇÃO APLICADA AQUI ---
    # Removemos a lógica de 'tier' e 'task' e apontamos
    # diretamente para o modelo que o 'ollama_service' cria.
    model_name = "vizu-llama3.2-mvp"
    # --- FIM DA ALTERAÇÃO ---

    try:
        print(f"INFO: Conectando ao Ollama ({settings.OLLAMA_BASE_URL}) com modelo: {model_name}")
        ollama_model = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=model_name,
            callbacks=callbacks
        )
        return ollama_model

    except Exception as e:
        print(f"ERRO: Falha crítica ao conectar ao Ollama ({e}).")
        raise ConnectionError(
            f"Não foi possível conectar ao Ollama em {settings.OLLAMA_BASE_URL}"
        )

def get_embedding_model() -> Embeddings:
    """
    Retorna um cliente para o microserviço de embedding da Vizu.

    Não carrega mais o modelo localmente, apenas se conecta à API.
    """
    settings = get_llm_settings()

    # --- ALTERAÇÃO APLICADA AQUI ---
    # Remove a lógica de carregar o modelo localmente e
    # instancia o nosso novo cliente de API.

    print(f"INFO: Conectando ao serviço de embedding em: {settings.EMBEDDING_SERVICE_URL}")
    try:
        return VizuEmbeddingAPIClient(base_url=settings.EMBEDDING_SERVICE_URL)
    except Exception as e:
        print(f"ERRO: Falha ao inicializar o cliente de embedding: {e}")
        raise e
    # --- FIM DA ALTERAÇÃO ---