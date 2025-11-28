from functools import lru_cache
from typing import Optional
import redis
from pydantic_settings import BaseSettings
from pydantic import Field
from fastapi import Depends
from sqlalchemy.orm import Session

from .redis_service import RedisService
from .context_service import ContextService
from vizu_db_connector.database import get_db_session

class ContextSettings(BaseSettings):
    # Suporte direto à URL do Redis (Padrão Docker)
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")

    # Fallback
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")

    # --- MUDANÇA AQUI ---
    # Adicionamos 'frozen': True para permitir o cache (lru_cache)
    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "frozen": True
    }
    # --------------------

@lru_cache
def get_context_settings() -> ContextSettings:
    return ContextSettings()

@lru_cache
def get_redis_pool(settings: ContextSettings = Depends(get_context_settings)) -> redis.ConnectionPool:
    # Prioriza URL se existir (Docker)
    if settings.REDIS_URL:
        return redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

    return redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )

def get_redis_client(pool: redis.ConnectionPool = Depends(get_redis_pool)) -> redis.Redis:
    return redis.Redis(connection_pool=pool)

def get_redis_service(client: redis.Redis = Depends(get_redis_client)) -> RedisService:
    # Passa o CLIENTE, não a URL!
    return RedisService(redis_client=client)

def get_context_service(
    db: Session = Depends(get_db_session),
    cache: RedisService = Depends(get_redis_service)
) -> ContextService:
    return ContextService(db_session=db, cache_service=cache)