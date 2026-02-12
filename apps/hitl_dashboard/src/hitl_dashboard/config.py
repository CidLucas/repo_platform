# apps/hitl_dashboard/src/hitl_dashboard/config.py
"""Configuration for HITL Dashboard."""

import os
from functools import lru_cache


class Settings:
    """Dashboard settings from environment."""

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Langfuse
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

    # Dashboard
    PAGE_SIZE: int = int(os.getenv("HITL_PAGE_SIZE", "20"))
    REFRESH_INTERVAL: int = int(os.getenv("HITL_REFRESH_INTERVAL", "30"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
