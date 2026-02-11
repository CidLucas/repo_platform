from functools import lru_cache

import redis
from fastapi import Depends
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

from vizu_db_connector.database import get_db_session

from .context_service import ContextService
from .redis_service import RedisService


class ContextSettings(BaseSettings):
    # Redis connection URL (required in production via REDIS_URL env var)
    REDIS_URL: str | None = None

    # Database backend selection:
    # True = PostgreSQL local (via SQLAlchemy/DATABASE_URL)
    # False = Supabase SDK (via SUPABASE_URL)
    USE_LOCAL_DB: bool = False

    model_config = {"env_file": ".env", "extra": "ignore", "frozen": True}


@lru_cache
def get_context_settings() -> ContextSettings:
    return ContextSettings()


@lru_cache
def get_redis_pool(
    settings: ContextSettings = Depends(get_context_settings),
) -> redis.ConnectionPool:
    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL is required but not set")
    return redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis_client(
    pool: redis.ConnectionPool = Depends(get_redis_pool),
) -> redis.Redis:
    return redis.Redis(connection_pool=pool)


def get_redis_service(client: redis.Redis = Depends(get_redis_client)) -> RedisService:
    return RedisService(redis_client=client)


def get_context_service(
    db: Session = Depends(get_db_session),
    cache: RedisService = Depends(get_redis_service),
) -> ContextService:
    settings = get_context_settings()
    use_supabase = not settings.USE_LOCAL_DB
    return ContextService(db_session=db, cache_service=cache, use_supabase=use_supabase)
