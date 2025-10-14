import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("uvicorn")


class Settings(BaseSettings):
    SERVICE_NAME: str = "clientes-finais-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    DATABASE_URL: str # Adicionamos a URL do banco de dados

    model_config = SettingsConfigDict(
        env_file=".env.example",
        env_file_encoding='utf-8',
        extra='ignore'
    )


@lru_cache
def get_settings() -> Settings:
    log.info("Carregando configurações do ambiente...")
    return Settings()