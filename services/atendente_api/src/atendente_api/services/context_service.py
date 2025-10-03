# src/atendente_api/services/context_service.py

from typing import Optional

from sqlalchemy.orm import Session, joinedload

# Modelos Pydantic para a estrutura do nosso contexto em cache
from atendente_api.core.schemas import VizuClientContext
# Serviço de Redis que já temos para salvar e carregar dados
from atendente_api.services.redis_service import RedisService
# Modelos SQLAlchemy da nossa biblioteca de banco de dados
from vizu_db_connector.models.cliente_vizu import ClienteVizu
from vizu_db_connector.models.configuracao import ConfiguracaoNegocio


class ContextService:
    """
    Serviço responsável por gerenciar o ciclo de vida do contexto do cliente.
    Implementa a estratégia de cache "Redis-First" para otimizar a performance.
    """

    def __init__(self, db_session: Session, redis_service: RedisService):
        self.db = db_session
        self.redis = redis_service

    def get_client_context(self, api_key: str) -> Optional[VizuClientContext]:
        """
        Obtém o contexto de um cliente Vizu a partir de sua chave de API.
        """
        redis_key = f"context:client:{api_key}"

        # 1. Estratégia Redis-First: Tenta buscar do cache
        cached_context = self.redis.load_pydantic_model(redis_key, VizuClientContext)
        if cached_context:
            print(f"Cache HIT para a api_key: {api_key[:8]}...")
            return cached_context

        print(f"Cache MISS para a api_key: {api_key[:8]}... Buscando no banco de dados.")

        # 2. Cache MISS: Busca no banco de dados
        cliente_db = (
            self.db.query(ClienteVizu)
            .options(joinedload(ClienteVizu.configuracao))
            .filter(ClienteVizu.api_key == api_key)
            .one_or_none()
        )

        if not cliente_db or not cliente_db.configuracao:
            return None

        # --- CORREÇÃO FINAL APLICADA AQUI ---
        # 3. Constrói o objeto de contexto Pydantic a partir dos modelos SQLAlchemy
        #    Garantimos que TODOS os campos do VizuClientContext sejam preenchidos.
        context_to_cache = VizuClientContext(
            id=cliente_db.id,
            api_key=cliente_db.api_key,
            nome_empresa=cliente_db.nome_empresa,
            prompt_base=cliente_db.configuracao.prompt_base,
            horario_funcionamento=cliente_db.configuracao.horario_funcionamento,
            ferramenta_rag_habilitada=cliente_db.configuracao.ferramenta_rag_habilitada,
            # Como o modelo do DB não tem 'ferramenta_sql_habilitada', fornecemos um padrão seguro.
            ferramenta_sql_habilitada=getattr(cliente_db.configuracao, 'ferramenta_sql_habilitada', False),
            credenciais=[] # Adicionado para completar o modelo
        )

        # 4. Salva o contexto recém-buscado no Redis com TTL de 24 horas
        self.redis.save_pydantic_model(redis_key, context_to_cache, ttl=86400)
        print(f"Contexto para {cliente_db.nome_empresa} salvo no Redis com TTL de 24h.")

        return context_to_cache