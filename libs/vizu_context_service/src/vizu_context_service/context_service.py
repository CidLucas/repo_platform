import asyncio
import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session

# Dependências
from vizu_db_connector import crud
from vizu_models.vizu_client_context import VizuClientContext
from .redis_service import RedisService

logger = logging.getLogger(__name__)

class ContextService:
    CACHE_KEY_PREFIX = "context:client:"
    CACHE_TTL_SECONDS = 300  # 5 minutos

    def __init__(self, db_session: Session, cache_service: RedisService):
        self.db = db_session
        self.cache = cache_service
        logger.info("ContextService inicializado.")

    def _get_cache_key(self, cliente_id: UUID) -> str:
        return f"{self.CACHE_KEY_PREFIX}{cliente_id}"

    async def get_client_context_by_api_key(self, api_key: str) -> Optional[VizuClientContext]:
        """
        Busca o contexto completo do cliente usando a API Key.
        1. Busca ID no Postgres (leve).
        2. Chama get_client_context_by_id (que tem cache pesado).
        """
        try:
            # 1. Busca rápida no DB para pegar o ID
            # Usamos to_thread pois o SQLAlchemy é síncrono
            cliente_db = await asyncio.to_thread(
                crud.get_cliente_vizu_by_api_key, self.db, api_key
            )

            if not cliente_db:
                return None

            # 2. Com o ID em mãos, buscamos o contexto completo (com cache)
            return await self.get_client_context_by_id(cliente_db.id)

        except Exception as e:
            logger.error(f"Erro na autenticação por API Key: {e}", exc_info=True)
            return None

    async def get_client_context_by_id(self, cliente_id: UUID) -> Optional[VizuClientContext]:
        """
        Recupera o contexto completo (Cliente + Configurações), usando Cache Redis.
        """
        cache_key = self._get_cache_key(cliente_id)

        # --- 1. TENTATIVA DE CACHE (REDIS) ---
        try:
            cached_data = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached_data:
                # Reconstrói o objeto Pydantic a partir do dicionário em cache
                try:
                    return VizuClientContext.model_validate(cached_data)
                except Exception as e:
                    logger.warning(f"Cache corrompido para {cliente_id}, invalidando... Erro: {e}")
                    await self.clear_context_cache(cliente_id)
        except Exception as e:
            logger.warning(f"Falha ao ler cache Redis: {e}")

        # --- 2. BUSCA NO BANCO DE DADOS (POSTGRES) ---
        try:
            # Busca o cliente com suas configurações (JOIN)
            cliente_db = await asyncio.to_thread(
                crud.get_cliente_vizu_by_id, self.db, cliente_id
            )

            if not cliente_db:
                logger.warning(f"Cliente {cliente_id} não encontrado no banco.")
                return None

            # --- 3. CONSTRUÇÃO BLINDADA DO CONTEXTO ---
            # A configuração foi migrada para colunas diretas em `cliente_vizu`.
            # Tratamos casos onde os campos são nulos
            prompt_base = getattr(cliente_db, "prompt_base", None) or "Você é um assistente útil."
            rag_enabled = bool(getattr(cliente_db, "ferramenta_rag_habilitada", False))
            sql_enabled = bool(getattr(cliente_db, "ferramenta_sql_habilitada", False))
            horario = getattr(cliente_db, "horario_funcionamento", {}) or {}
            collection = getattr(cliente_db, "collection_rag", "default_collection")

            # Monta o objeto final plano (Flat) para a aplicação usar
            client_context = VizuClientContext(
                id=cliente_db.id,
                api_key=cliente_db.api_key,
                nome_empresa=cliente_db.nome_empresa,
                tipo_cliente=cliente_db.tipo_cliente, # Assume que o Enum ou string bate
                tier=cliente_db.tier,

                # Configurações
                prompt_base=prompt_base,
                horario_funcionamento=horario,
                ferramenta_rag_habilitada=rag_enabled,
                ferramenta_sql_habilitada=sql_enabled,
                collection_rag=collection,

                credenciais=[] # Lista vazia por padrão
            )

            # --- 4. SALVAR NO CACHE ---
            # Salva para que a próxima requisição seja rápida
            await asyncio.to_thread(
                self.cache.set_json,
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS
            )

            return client_context

        except Exception as e:
            logger.error(f"Erro crítico ao montar contexto para {cliente_id}: {e}", exc_info=True)
            return None

    async def clear_context_cache(self, cliente_id: UUID) -> None:
        """Remove o contexto do cache (útil após updates no cliente)."""
        cache_key = self._get_cache_key(cliente_id)
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Cache invalidado para: {cliente_id}")