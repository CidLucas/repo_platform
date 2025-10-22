from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Optional
# Dependências de outras libs (que já são agnósticas)
from vizu_db_connector import crud
from vizu_shared_models.cliente_vizu import VizuClientContext # Supondo o nome do modelo

from .redis_service import RedisService

logger = logging.getLogger(__name__)

class ContextService:
    """
    Classe de serviço agnóstica para gerenciar o contexto do cliente Vizu.

    Esta classe orquestra a obtenção de dados do cliente, utilizando
    cache (via RedisService) e o banco de dados (via Session)
    para construir o VizuClientContext.
    """

    CACHE_KEY_PREFIX = "context:client:"
    CACHE_TTL_SECONDS = 300 # 5 minutos

    def __init__(self, db_session: Session, cache_service: RedisService):
        """
        Inicializa o serviço com suas dependências.

        Args:
            db_session: Uma sessão SQLAlchemy.
            cache_service: Uma instância do nosso RedisService agnóstico.
        """
        self.db = db_session
        self.cache = cache_service
        logger.info("ContextService inicializado.")

    def _get_cache_key(self, cliente_id: UUID) -> str:
        """Helper para gerar a chave de cache padronizada."""
        return f"{self.CACHE_KEY_PREFIX}{cliente_id}"

    def get_client_context_by_id(self, cliente_id: UUID) -> Optional[VizuClientContext]:
        """
        Obtém o contexto completo do cliente, usando cache.
        """
        if not cliente_id:
            logger.warning("Tentativa de obter contexto com cliente_id nulo.")
            return None

        cache_key = self._get_cache_key(cliente_id)

        # 1. Tentar obter do Cache
        cached_context_dict = self.cache.get_json(cache_key)
        if cached_context_dict:
            try:
                # Desserializa do dict para o modelo Pydantic
                return VizuClientContext.model_validate(cached_context_dict)
            except Exception as e:
                logger.error(f"Falha ao validar contexto do cache {cache_key}: {e}")
                # Cache está corrompido, deletar
                self.cache.delete(cache_key)

        logger.debug(f"Cache miss. Buscando contexto no DB para: {cliente_id}")

        # 2. Se falhar, buscar no Banco de Dados
        try:
            # Esta função (ex: crud.get_full_client_context) deve ser criada
            # na libs/vizu_db_connector e fazer os joins necessários
            # para montar o VizuClientContext (cliente, config, credenciais, etc.)

            # SUPONDO que o crud.get_cliente_vizu_by_id já faz os joins
            cliente_db = crud.get_cliente_vizu_by_id(self.db, cliente_id)

            if not cliente_db:
                logger.warning(f"Contexto não encontrado no DB para: {cliente_id}")
                return None

            # Constrói o modelo Pydantic a partir do modelo SQLAlchemy
            # (Isto pode exigir uma lógica de mapeamento mais complexa)
            client_context = VizuClientContext.model_validate(cliente_db)

            # 3. Armazenar no Cache
            self.cache.set_json(
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS
            )

            return client_context

        except Exception as e:
            logger.error(f"Erro de DB ao buscar contexto para {cliente_id}: {e}")
            return None

    def clear_context_cache(self, cliente_id: UUID) -> None:
        """Invalida (deleta) o cache para um cliente específico."""
        cache_key = self._get_cache_key(cliente_id)
        self.cache.delete(cache_key)
        logger.info(f"Cache de contexto invalidado para: {cliente_id}")