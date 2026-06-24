
from __future__ import annotations
from functools import lru_cache

import redis
from fastapi import Depends
from pydantic_settings import BaseSettings

from blu_context_service.context_service import ContextService
from blu_context_service.redis_service import RedisService


class ContextSettings(BaseSettings):
    REDIS_URL: str | None = None

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
    cache: RedisService = Depends(get_redis_service),
) -> ContextService:
    return ContextService(cache_service=cache)
