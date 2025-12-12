"""
Cache Service para Analytics API usando Redis.

Implementa cache com TTL configurável para otimizar queries pesadas.
"""
import json
import logging
from typing import Any, Optional
from datetime import datetime

import redis.asyncio as redis
from analytics_api.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Serviço de cache assíncrono usando Redis."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    async def get_client(self) -> redis.Redis:
        """Retorna ou cria conexão com Redis."""
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client
    
    async def get(self, key: str) -> Optional[dict]:
        """
        Busca valor no cache.
        
        Returns:
            dict com value e metadata, ou None se não encontrado
        """
        try:
            client = await self.get_client()
            cached = await client.get(key)
            
            if cached is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            ttl = await client.ttl(key)
            data = json.loads(cached)
            
            logger.debug(f"Cache HIT: {key} (TTL: {ttl}s)")
            return {
                "data": data,
                "cached": True,
                "ttl": ttl
            }
        except redis.RedisError as e:
            logger.warning(f"Redis error on get: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Armazena valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a armazenar (será serializado para JSON)
            ttl: Time-to-live em segundos (usa default se não especificado)
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            client = await self.get_client()
            ttl = ttl or settings.CACHE_TTL_SECONDS
            
            serialized = json.dumps(value, default=str)
            await client.setex(key, ttl, serialized)
            
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis error on set: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Remove chave do cache."""
        try:
            client = await self.get_client()
            await client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis error on delete: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalida todas as chaves que correspondem ao padrão.
        
        Args:
            pattern: Padrão glob (ex: "analytics:orders:*")
        
        Returns:
            Número de chaves removidas
        """
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await client.delete(*keys)
                logger.info(f"Cache INVALIDATE: {len(keys)} keys matching '{pattern}'")
            
            return len(keys)
        except redis.RedisError as e:
            logger.warning(f"Redis error on invalidate: {e}")
            return 0
    
    async def close(self):
        """Fecha conexão com Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    @staticmethod
    def build_key(*parts: str) -> str:
        """Constrói chave de cache a partir de partes."""
        return ":".join(["analytics"] + list(parts))


# Singleton global
cache_service = CacheService()
