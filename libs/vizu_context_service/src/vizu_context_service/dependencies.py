from functools import lru_cache
from typing import Generator
import redis
from pydantic_settings import BaseSettings
from pydantic import Field
from fastapi import Depends
from sqlalchemy.orm import Session

# Importa as classes de serviço AGnÓSTICAS
from .redis_service import RedisService
from .context_service import ContextService

# Importa o injetor de sessão de DB da outra lib
from vizu_db_connector.database import get_db_session

# --- Configuração de Conexão com Redis ---
# (Pode ser movido para um arquivo config.py se crescer)
class ContextSettings(BaseSettings):
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_context_settings() -> ContextSettings:
    return ContextSettings()

# --- Pool de Conexão Redis ---
# Criamos um pool de conexão singleton para ser reutilizado
@lru_cache
def get_redis_pool(settings: ContextSettings = Depends(get_context_settings)) -> redis.ConnectionPool:
    """Cria um pool de conexão Redis singleton."""
    return redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True # Importante para o json.loads
    )

def get_redis_client(
    pool: redis.ConnectionPool = Depends(get_redis_pool)
) -> Generator[redis.Redis, None, None]:
    """Injetor de dependência para um cliente Redis."""
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        # Clientes de pool não precisam ser fechados,
        # a conexão é gerenciada pelo pool.
        pass

# --- Singletons dos Serviços ---

@lru_cache
def get_redis_service_singleton(
    client: redis.Redis = Depends(get_redis_client) # <--- Erro comum: precisa ser Depends
) -> RedisService:
    """
    Injetor singleton para o RedisService.
    Reutiliza a mesma instância de cliente Redis.
    """
    # NOTA: O lru_cache aqui pode ser problemático se o 'client'
    #       for um gerador. Vamos simplificar para injeção direta.
    pass # Removendo lru_cache para evitar complexidade com gerador

# --- Abordagem Correta para Singletons com FastAPI ---

# O lru_cache é melhor em funções sem 'Depends'.
# Para serviços, é mais seguro instanciar e depender.

def get_redis_service(
    client: redis.Redis = Depends(get_redis_client)
) -> RedisService:
    """Injeta uma instância do RedisService agnóstico."""
    return RedisService(redis_client=client)

def get_context_service(
    db: Session = Depends(get_db_session), # Da vizu_db_connector
    cache: RedisService = Depends(get_redis_service) # Daqui de cima
) -> ContextService:
    """
    Injeta uma instância do ContextService agnóstico,
    já populada com as dependências (DB e Cache).
    """
    return ContextService(db_session=db, cache_service=cache)

# --- FIM ---
# O services/atendente_core irá importar:
# from vizu_context_service.dependencies import get_context_service
# ... e usá-lo:
# service: ContextService = Depends(get_context_service)