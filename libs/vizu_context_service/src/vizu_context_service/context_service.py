import asyncio
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Optional
# Dependências de outras libs (agora vizu_models substituiria vizu_models)
from vizu_db_connector import crud
# Assumindo que VizuClientContext foi movido para vizu_models
from vizu_models.vizu_client_context import VizuClientContext

from .redis_service import RedisService

logger = logging.getLogger(__name__)

class ContextService:
    # ... (Seu __init__, _get_cache_key e clear_context_cache permanecem iguais) ...
    CACHE_KEY_PREFIX = "context:client:"
    CACHE_TTL_SECONDS = 300 # 5 minutos

    def __init__(self, db_session: Session, cache_service: RedisService):
        self.db = db_session
        self.cache = cache_service
        logger.info("ContextService inicializado.")

    def _get_cache_key(self, cliente_id: UUID) -> str:
        return f"{self.CACHE_KEY_PREFIX}{cliente_id}"

    # =========================================================================
    # == FUNÇÃO DE BUSCA PRIMÁRIA (Pelo ID)
    # =========================================================================

    async def get_client_context_by_id(self, cliente_id: UUID) -> Optional[VizuClientContext]:
        # ... (Sua lógica existente, que busca no cache e no DB) ...
        #

        cache_key = self._get_cache_key(cliente_id)
        cached_context_dict = await asyncio.to_thread(self.cache.get_json, cache_key)

        if cached_context_dict:
            try:
                return VizuClientContext.model_validate(cached_context_dict)
            except Exception as e:
                logger.error(f"Falha ao validar contexto do cache {cache_key}: {e}")
                await asyncio.to_thread(self.cache.delete, cache_key)

        logger.debug(f"Cache miss. Buscando contexto no DB para: {cliente_id}")

        try:
            # SUPONDO que o crud.get_cliente_vizu_by_id já faz os joins
            cliente_db = await asyncio.to_thread(
                crud.get_cliente_vizu_by_id, self.db, cliente_id
            )

            if not cliente_db:
                logger.warning(f"Contexto não encontrado no DB para: {cliente_id}")
                return None

            # Constrói o modelo Pydantic a partir do modelo SQLAlchemy
            client_context = VizuClientContext.model_validate(cliente_db)

            await asyncio.to_thread(
                self.cache.set_json,
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS
            )

            return client_context

        except Exception as e:
            logger.error(f"Erro de DB ao buscar contexto para {cliente_id}: {e}")
            return None

    # =========================================================================
    # == NOVO: FUNÇÃO DE AUTENTICAÇÃO (Pela API Key)
    # =========================================================================

    async def get_client_context_by_api_key(self, api_key: str) -> Optional[VizuClientContext]:
        """
        Busca o contexto completo do cliente usando a API Key.
        Este é o endpoint de autenticação do Atendente Core.
        """
        api_key_hash = api_key[:8] # Logging seguro
        logger.info(f"ContextService: Tentativa de autenticação pela API Key (hash: {api_key_hash}...)")

        try:
            # 1. Tentar buscar o cliente no DB pela API Key
            # Chamada síncrona do novo CRUD
            cliente_db = await asyncio.to_thread(
                crud.get_cliente_vizu_by_api_key, self.db, api_key
            )

            if not cliente_db:
                logger.warning(f"Autenticação falhou. Cliente não encontrado no DB para API Key (hash: {api_key_hash}...)")
                return None

            cliente_id = cliente_db.id # Obtemos o ID (UUID)

            # 2. Reutilizar a lógica de cache/contexto
            # O get_client_context_by_id fará a verificação de cache, joins, etc.
            client_context = await self.get_client_context_by_id(cliente_id)

            if client_context:
                 logger.info(f"Autenticação SUCESSO. Contexto recuperado para {client_context.nome_empresa} (ID: {cliente_id})")

            return client_context

        except Exception as e:
            logger.error(f"Erro inesperado no fluxo de autenticação por API Key [Type: {type(e).__name__}]: {e}", exc_info=True)
            return None


    async def clear_context_cache(self, cliente_id: UUID) -> None:
        """Invalida (deleta) o cache para um cliente específico."""
        cache_key = self._get_cache_key(cliente_id)
        # (usando asyncio.to_thread para I/O síncrono)
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Cache de contexto invalidado para: {cliente_id}")