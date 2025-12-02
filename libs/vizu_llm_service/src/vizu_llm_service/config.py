from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class LLMSettings(BaseSettings):
    """
    Configurações para o Vizu LLM Service.

    Suporta múltiplos providers:
    - Ollama Local (ollama_service container)
    - Ollama Cloud (api.ollama.com)
    - OpenAI (API)
    - Anthropic (API)
    - Google Gemini (API)
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ========================================================================
    # PROVIDER DEFAULT
    # ========================================================================
    # Provider padrão: ollama, ollama_cloud, openai, anthropic, google
    LLM_PROVIDER: str = Field(default="ollama_cloud")

    # ========================================================================
    # OLLAMA (LOCAL)
    # ========================================================================
    OLLAMA_BASE_URL: str = Field(default="http://ollama_service:11434")

    # ========================================================================
    # OLLAMA CLOUD (ollama.com/cloud - via HTTP client direto)
    # Ref: https://docs.ollama.com/cloud
    # ========================================================================
    OLLAMA_CLOUD_API_KEY: str | None = Field(default=None)
    OLLAMA_CLOUD_BASE_URL: str = Field(default="https://ollama.com")
    OLLAMA_CLOUD_DEFAULT_MODEL: str = Field(default="llama3.2")

    # ========================================================================
    # EMBEDDING SERVICE
    # ========================================================================
    EMBEDDING_SERVICE_URL: str = Field(default="http://embedding_service:11435")

    # ========================================================================
    # LANGFUSE (OBSERVABILITY)
    # ========================================================================
    LANGFUSE_HOST: str | None = Field(default="https://cloud.langfuse.com")
    LANGFUSE_PUBLIC_KEY: str | None = Field(default=None)
    LANGFUSE_SECRET_KEY: str | None = Field(default=None)

    # ========================================================================
    # OPENAI
    # ========================================================================
    OPENAI_API_KEY: str | None = Field(default=None)
    OPENAI_BASE_URL: str | None = Field(default=None)  # Para proxies/Azure

    # ========================================================================
    # ANTHROPIC
    # ========================================================================
    ANTHROPIC_API_KEY: str | None = Field(default=None)

    # ========================================================================
    # GOOGLE GEMINI
    # ========================================================================
    GOOGLE_API_KEY: str | None = Field(default=None)

    @property
    def langfuse_enabled(self) -> bool:
        """Langfuse está habilitado se tiver public e secret key."""
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def ollama_cloud_enabled(self) -> bool:
        """Ollama Cloud está habilitado se tiver API key."""
        return bool(self.OLLAMA_CLOUD_API_KEY)

    @property
    def openai_enabled(self) -> bool:
        """OpenAI está habilitado se tiver API key."""
        return bool(self.OPENAI_API_KEY)

    @property
    def anthropic_enabled(self) -> bool:
        """Anthropic está habilitado se tiver API key."""
        return bool(self.ANTHROPIC_API_KEY)

    @property
    def google_enabled(self) -> bool:
        """Google Gemini está habilitado se tiver API key."""
        return bool(self.GOOGLE_API_KEY)


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Retorna as configurações de LLM (cached)."""
    return LLMSettings()


def clear_settings_cache():
    """Limpa o cache das configurações (útil para testes)."""
    get_llm_settings.cache_clear()