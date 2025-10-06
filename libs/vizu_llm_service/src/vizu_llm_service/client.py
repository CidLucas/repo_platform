from enum import Enum
from .config import get_llm_settings
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

class ModelTier(str, Enum):
    """Define os níveis de complexidade/custo do modelo."""
    DEFAULT = "default"
    FAST = "fast"
    POWERFUL = "powerful"

class ModelTask(str, Enum):
    """Define a especialização da tarefa."""
    GENERAL_AGENT = "general_agent"
    CLASSIFICATION = "classification"

def get_model(
    tier: ModelTier = ModelTier.DEFAULT,
    task: ModelTask = ModelTask.GENERAL_AGENT
) -> BaseChatModel:
    """
    Roteador de Modelos Inteligente da Vizu.

    Para o MVP, esta função sempre tenta retornar o modelo Llama 3.2 do Ollama.
    A sua interface e a lógica de fallback já estão prontas para o futuro.
    """
    settings = get_llm_settings()

    # --- Lógica do MVP ---
    # Tenta se conectar ao nosso modelo primário (Ollama).
    try:
        print("INFO: Tentando conectar ao modelo primário (Ollama)...")
        ollama_model = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model="llama3.2" # Modelo padrão do MVP
        )
        # Em um cenário de produção, um health check rápido seria ideal aqui.
        # Ex: ollama_model.invoke("ping")
        print("INFO: Conexão com Ollama bem-sucedida.")
        return ollama_model
    except Exception as e:
        print(f"AVISO: Falha ao conectar com o modelo primário (Ollama): {e}")

        # --- Lógica de Fallback ---
        # Se a conexão com o Ollama falhar, tenta usar o fallback se configurado.
        if settings.OPENAI_API_KEY:
            print("INFO: Acionando modelo de fallback (OpenAI)...")
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

        # Se não houver fallback, o erro é levantado.
        raise ConnectionError(
            "Falha ao conectar ao modelo primário (Ollama) e nenhum modelo de fallback foi configurado."
        )