"""
Vendas Agent configuration.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("uvicorn")


class Settings(BaseSettings):
    """
    Manages application settings in a centralized and validated way.
    """

    # Service name for observability
    SERVICE_NAME: str = "vendas-agent"

    # Dependent service endpoints
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    DATABASE_URL: str
    REDIS_URL: str
    MCP_SERVER_URL: str = "http://tool_pool_api:9000/mcp/"

    # Langfuse configuration (optional)
    LANGFUSE_HOST: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a singleton cached instance of settings.
    """
    log.info("Loading environment settings for vendas_agent...")
    return Settings()
