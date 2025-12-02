# vizu_experiment_service/config.py
"""Configuration for the experiment service."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class ExperimentSettings(BaseSettings):
    """Settings for experiment execution."""

    # API Configuration
    ATENDENTE_API_URL: str = "http://localhost:8003"
    API_TIMEOUT_SECONDS: int = 60
    MAX_PARALLEL_REQUESTS: int = 5
    RETRY_COUNT: int = 2

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/vizu_db"

    # Redis (for HITL queue)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Langfuse
    LANGFUSE_HOST: str = "http://localhost:3000"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # HITL defaults
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.7
    DEFAULT_SAMPLE_RATE: float = 0.1

    # Experiments directory
    EXPERIMENTS_DIR: str = "experiments"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_experiment_settings() -> ExperimentSettings:
    """Get cached experiment settings."""
    return ExperimentSettings()


# Global settings instance
settings = get_experiment_settings()
