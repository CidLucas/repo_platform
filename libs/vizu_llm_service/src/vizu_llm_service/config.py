from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class LLMSettings(BaseSettings):
    """
    Configurações para o Vizu LLM Service.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # URL do Ollama (LLM)
    OLLAMA_BASE_URL: str = "http://ollama_service:11434"

    # --- ADICIONADO: URL do Serviço de Embedding ---
    # Por padrão aponta para o nome do container no docker-compose
    EMBEDDING_SERVICE_URL: str = "http://embedding_service:11435"

    # Langfuse (Mantido)
    LANGFUSE_HOST: str | None = Field(default=None)
    LANGFUSE_PUBLIC_KEY: str | None = Field(default=None)
    LANGFUSE_SECRET_KEY: str | None = Field(default=None)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.LANGFUSE_HOST and self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

@lru_cache
def get_llm_settings() -> LLMSettings:
    return LLMSettings()