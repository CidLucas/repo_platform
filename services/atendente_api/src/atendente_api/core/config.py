# src/atendente_api/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    """
    Define as configurações da aplicação, lidas de variáveis de ambiente.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Variáveis essenciais
    REDIS_URL: str
    LANGCHAIN_API_KEY: str
    TWILIO_AUTH_TOKEN: str

    # Adicione outras variáveis aqui conforme necessário
    # OPENAI_API_KEY: str
    DATABASE_URL: str

    # Ambiente de execução do serviço
    ENVIRONMENT: Literal['development', 'staging', 'production'] = 'development'

    # Configurações de Observabilidade (LangSmith)
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "atendente-virtual-api"

    # URL do serviço de gerenciamento de clientes/credenciais
    # Em um ambiente real, este seria o endpoint para buscar
    # as credenciais do Twilio, Google, etc., associadas a um client_id.
    CLIENTS_API_URL: str = "http://localhost:8001/api/v1" # Exemplo

    # Configurações do Redis para cache de sessão
    REDIS_PORT: int = 6379



@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma instância das configurações.
    O decorator @lru_cache garante que a classe Settings seja instanciada
    apenas uma vez (padrão singleton), mas de forma "preguiçosa",
    somente quando esta função for chamada pela primeira vez.
    """
    return Settings()




