from functools import lru_cache

import redis
from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

from vizu_db_connector.database import get_db_session

from .context_service import ContextService
from .redis_service import RedisService


class ContextSettings(BaseSettings):
    # Suporte direto à URL do Redis (Padrão Docker)
    REDIS_URL: str | None = Field(None, env="REDIS_URL")

    # Fallback
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")

    # Database backend selection:
    # True = PostgreSQL local (via SQLAlchemy/DATABASE_URL)
    # False = Supabase SDK (via SUPABASE_URL)
    USE_LOCAL_DB: bool = Field(default=False, env="USE_LOCAL_DB")

    model_config = {"env_file": ".env", "extra": "ignore", "frozen": True}


@lru_cache
def get_context_settings() -> ContextSettings:
    return ContextSettings()


@lru_cache
def get_redis_pool(
    settings: ContextSettings = Depends(get_context_settings),
) -> redis.ConnectionPool:
    # Prioriza URL se existir (Docker)
    if settings.REDIS_URL:
        return redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

    return redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )


def get_redis_client(
    pool: redis.ConnectionPool = Depends(get_redis_pool),
) -> redis.Redis:
    return redis.Redis(connection_pool=pool)


def get_redis_service(client: redis.Redis = Depends(get_redis_client)) -> RedisService:
    # Passa o CLIENTE, não a URL!
    return RedisService(redis_client=client)


def get_context_service(
    db: Session = Depends(get_db_session),
    cache: RedisService = Depends(get_redis_service),
) -> ContextService:
    settings = get_context_settings()
    # USE_LOCAL_DB=True -> SQLAlchemy (PostgreSQL local)
    # USE_LOCAL_DB=False -> Supabase SDK (cloud)
    use_supabase = not settings.USE_LOCAL_DB
    return ContextService(db_session=db, cache_service=cache, use_supabase=use_supabase)
