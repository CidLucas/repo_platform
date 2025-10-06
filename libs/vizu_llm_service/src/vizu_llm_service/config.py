from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class LLMSettings(BaseSettings):
    """
    Configurações para o Vizu LLM Service.

    Carrega variáveis de ambiente para configurar a conexão com
    os provedores de modelos de linguagem.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # URL base do nosso servidor Ollama interno.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Chave de API para o modelo de fallback (ex: OpenAI), que é opcional.
    OPENAI_API_KEY: str | None = None

@lru_cache
def get_llm_settings() -> LLMSettings:
    """
    Retorna uma instância singleton das configurações do LLM Service.
    O uso de @lru_cache garante que as variáveis de ambiente sejam lidas
    e validadas apenas uma vez.
    """
    return LLMSettings()