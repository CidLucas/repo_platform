# src/atendente_api/services/redis_service.py

import redis
from typing import Type, TypeVar
from pydantic import BaseModel

# --- CORREÇÃO APLICADA AQUI ---
# Importa a FUNÇÃO que obtém as configurações, não mais a instância global.
from atendente_api.core.config import get_settings

# Define um tipo genérico para nossas funções que usam modelos Pydantic
PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class RedisService:
    """
    Serviço especializado para interagir com o Redis, encapsulando a lógica
    de serialização e cache para as necessidades do Atendente API.
    """
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client

    def save_pydantic_model(
        self, key: str, model_instance: PydanticModel, ttl: int | None = None
    ):
        json_data = model_instance.model_dump_json()
        self.client.set(key, json_data, ex=ttl)

    def load_pydantic_model(
        self, key: str, model_class: Type[PydanticModel]
    ) -> PydanticModel | None:
        json_data = self.client.get(key)
        if json_data:
            return model_class.model_validate_json(json_data)
        return None


# --- Função de Dependência para FastAPI ---

# A criação do pool de conexões agora também usa a função get_settings()
# para garantir que ela só seja executada quando necessário.
def get_redis_pool() -> redis.ConnectionPool:
    settings = get_settings()
    return redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

def get_redis_service() -> RedisService:
    """
    Dependência do FastAPI que fornece uma instância do RedisService.
    """
    pool = get_redis_pool()
    redis_client = redis.Redis(connection_pool=pool)
    yield RedisService(redis_client)