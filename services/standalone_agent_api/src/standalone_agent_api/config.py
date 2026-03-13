"""Configuration for standalone agent API service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    # Service
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # MCP and agents
    TOOL_POOL_API_URL: str = "http://tool_pool_api:8000/mcp/"
    REDIS_URL: str = "redis://redis:6379"

    # Langfuse observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://us.cloud.langfuse.com"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Agent caching
    MAX_CACHED_AGENTS: int = 100  # LRU cache for compiled graphs
    CHECKPOINT_TTL_SECONDS: int = 86400  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
