# libs/vizu_llm_service/src/vizu_llm_service/config.py

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class LLMSettings(BaseSettings):
    """
    Configurações para o Vizu LLM Service.
    Carrega variáveis de ambiente para configurar a conexão com
    os provedores de modelos de linguagem.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # URL base do nosso servidor Ollama interno.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- REMOVIDO ---
    # OPENAI_API_KEY: str | None = None

    # --- ADICIONADO ---
    # Define o modelo de embedding padrão do Hugging Face.
    # Usaremos um modelo leve e popular.
    DEFAULT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Configurações do Langfuse (permanecem)
    LANGFUSE_HOST: str | None = Field(default=None)
    LANGFUSE_PUBLIC_KEY: str | None = Field(default=None)
    LANGFUSE_SECRET_KEY: str | None = Field(default=None)

    @property
    def langfuse_enabled(self) -> bool:
        """Verifica se todas as variáveis do Langfuse estão configuradas."""
        return bool(
            self.LANGFUSE_HOST
            and self.LANGFUSE_PUBLIC_KEY
            and self.LANGFUSE_SECRET_KEY
        )

@lru_cache
def get_llm_settings() -> LLMSettings:
    """
    Retorna uma instância singleton das configurações do LLM Service.
    """
    return LLMSettings()