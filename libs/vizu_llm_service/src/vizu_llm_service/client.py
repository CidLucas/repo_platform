# libs/vizu_llm_service/src/vizu_llm_service/client.py

from enum import Enum
from .config import get_llm_settings, LLMSettings
from langchain_community.chat_models import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks.base import BaseCallbackHandler
from typing import List, Optional

# --- INÍCIO: Imports de Embeddings Locais ---
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings # Pacote moderno
# --- FIM: Imports de Embeddings Locais ---

# --- REMOVIDO ---
# from langchain_openai import ChatOpenAI
# from langchain_openai import OpenAIEmbeddings

# --- INÍCIO: Imports do Langfuse ---
from langfuse.langchain import CallbackHandler
# --- FIM: Imports do Langfuse ---


class ModelTier(str, Enum):
    """Define os níveis de complexidade/custo do modelo."""
    DEFAULT = "default"
    FAST = "fast"
    POWERFUL = "powerful"

class ModelTask(str, Enum):
    """Define a especialização da tarefa."""
    GENERAL_AGENT = "general_agent"
    CLASSIFICATION = "classification"

def _get_langfuse_callback(settings: LLMSettings) -> Optional[CallbackHandler]:
    """
    Função helper para inicializar o handler do Langfuse.
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
    """ Retorna a lista de callbacks base (incluindo Langfuse) """
    callbacks: List[BaseCallbackHandler] = []
    langfuse_handler = _get_langfuse_callback(settings)
    if langfuse_handler:
        callbacks.append(langfuse_handler)
    return callbacks

def get_model(
    tier: ModelTier = ModelTier.DEFAULT,
    task: ModelTask = ModelTask.GENERAL_AGENT
) -> BaseChatModel:
    """
    Roteador de Modelos Inteligente da Vizu.

    Conecta-se ao Ollama e seleciona o modelo com base no Tier.
    """
    settings = get_llm_settings()
    callbacks = _get_base_callbacks(settings)

    # Mapeia nossos Tiers para modelos específicos do Ollama
    # (Valores de exemplo, ajuste conforme seus modelos locais)
    model_map = {
        ModelTier.FAST: "phi3:mini",
        ModelTier.POWERFUL: "llama3.2:latest",
        ModelTier.DEFAULT: "llama3.2:latest"
    }

    # Mapeamento de Tarefas (Exemplo: se classificação usar um modelo específico)
    if task == ModelTask.CLASSIFICATION:
        model_name = model_map[ModelTier.FAST]
    else:
        model_name = model_map[tier]

    try:
        print(f"INFO: Conectando ao Ollama ({settings.OLLAMA_BASE_URL}) com modelo: {model_name}")
        ollama_model = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=model_name,
            callbacks=callbacks
        )
        # TODO: Adicionar um health check simples se necessário
        return ollama_model

    except Exception as e:
        print(f"ERRO: Falha crítica ao conectar ao Ollama ({e}).")
        raise ConnectionError(
            f"Não foi possível conectar ao Ollama em {settings.OLLAMA_BASE_URL}"
        )

def get_embedding_model() -> Embeddings:
    """
    Roteador de Modelos de Embedding da Vizu.

    Fornece uma instância de um modelo de embedding local
    usando HuggingFace Transformers.
    """
    settings = get_llm_settings()
    model_name = settings.DEFAULT_EMBEDDING_MODEL

    # Define para rodar em CPU por padrão
    # (Pode ser alterado para 'cuda' se houver GPU disponível)
    model_kwargs = {'device': 'cpu'}

    print(f"INFO: Carregando modelo de embedding local: {model_name}")
    try:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs
        )
    except Exception as e:
        print(f"ERRO: Falha ao carregar modelo de embedding '{model_name}'.")
        print("Verifique se 'sentence-transformers' está instalado.")
        raise e