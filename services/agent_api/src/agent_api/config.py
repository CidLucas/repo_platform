"""Centralised settings for agent_api."""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("uvicorn")


class Settings(BaseSettings):
    SERVICE_NAME: str = "agent-api"
    LOG_LEVEL: str = "INFO"

    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379"
    DATABASE_URL: str | None = None
    # Direct session-mode connection (port 5432) — use for heavy jobs: ETL, bulk deletes.
    DATABASE_URL_DIRECT: str | None = None

    # MCP
    MCP_SERVER_URL: str = "http://tool_pool_api:8000/mcp/"
    MCP_URL: str | None = None

    # LLM
    LLM_PROVIDER: str = "openai"

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"

    # Conversation
    SESSION_HISTORY_WINDOW: int = 10
    MAX_PROMPT_TOKENS: int = 120_000
    CHARS_PER_TOKEN: int = 4

    # Routine dispatch
    ROUTINE_DISPATCH_TOKEN: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    log.info("Loading agent_api settings...")
    return Settings()
