import redis
import json
from typing import Any, Optional
import logging

# Configura um logger padrão para a biblioteca
logger = logging.getLogger(__name__)


class RedisService:
    """
    Classe de serviço agnóstica para interagir com o Redis.

    Esta classe não tem conhecimento do FastAPI. Ela recebe uma
    instância de cliente Redis e a utiliza para operações de cache.
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Inicializa o serviço com um cliente Redis conectado.

        Args:
            redis_client: Uma instância de redis.Redis.
        """
        self.client = redis_client
        logger.info("RedisService inicializado com cliente.")

    def set_json(self, key: str, data: Any, ttl_seconds: int = 3600) -> None:
        """
        Serializa um objeto (como um modelo Pydantic) para JSON e o armazena no cache.
        """
        try:
            # Assumindo que 'data' pode ser um modelo Pydantic, usamos .model_dump_json()
            if hasattr(data, "model_dump_json"):
                json_data = data.model_dump_json()
            else:
                json_data = json.dumps(data)

            self.client.setex(name=key, time=ttl_seconds, value=json_data)
            logger.debug(f"Cache SET para a chave: {key}")
        except redis.RedisError as e:
            logger.error(f"Erro ao SETAR cache para a chave {key}: {e}")
        except TypeError as e:
            logger.error(f"Erro de serialização JSON ao SETAR cache para {key}: {e}")

    def get_json(self, key: str) -> Optional[dict]:
        """
        Recupera um valor JSON do cache e o desserializa para um dicionário.
        """
        try:
            cached_data = self.client.get(key)
            if cached_data:
                logger.debug(f"Cache HIT para a chave: {key}")
                return json.loads(cached_data)

            logger.debug(f"Cache MISS para a chave: {key}")
            return None
        except redis.RedisError as e:
            logger.error(f"Erro ao LER cache da chave {key}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erro de desserialização JSON ao LER cache {key}: {e}")
            return None

    def delete(self, key: str) -> None:
        """Deleta uma chave do cache."""
        try:
            self.client.delete(key)
            logger.debug(f"Cache DELETE para a chave: {key}")
        except redis.RedisError as e:
            logger.error(f"Erro ao DELETAR cache da chave {key}: {e}")
