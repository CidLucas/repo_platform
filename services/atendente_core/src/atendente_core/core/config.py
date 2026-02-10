import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("uvicorn")


class Settings(BaseSettings):
    """
    Gerencia as configurações da aplicação de forma centralizada e validada.
    """

    # Nome do serviço para observabilidade
    SERVICE_NAME: str = "atendente-api"

    # Endpoints de serviços dependentes
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    # Credenciais e chaves de API
    LANGCHAIN_API_KEY: str | None = None  # Opcional, para LangSmith

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma instância única (singleton) e cacheada das configurações.
    """
    log.info("Carregando configurações do ambiente para o atendente_core...")
    return Settings()
