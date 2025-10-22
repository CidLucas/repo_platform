import logging
from typing import AsyncGenerator

from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from fastapi import Depends

# 1. Importa nosso loader de configuração
from tool_pool_api.core.config import get_settings, Settings

# 2. Importa as fábricas e serviços das nossas libs (Fase 1)
from vizu_context_service.context_service import ContextService
from vizu_context_service.dependencies import get_redis_client as get_vizu_redis_client # Renomeado para evitar conflito
from vizu_context_service.redis_service import RedisService
from vizu_db_connector.database import SessionLocal

# Configura o logger
logger = logging.getLogger(__name__)

# --- Funções de Injeção de Dependência ---

def get_app_settings() -> Settings:
    """Retorna uma instância singleton cacheada das configurações da aplicação."""
    return get_settings()


def get_db_session_factory(
    settings: Settings = Depends(get_app_settings)
) -> SessionLocal:
    """
    Retorna a fábrica de sessões do banco de dados (Vizu DB).
    Esta fábrica será usada pelo ContextService para buscar dados quando o cache falhar.
    """
    # Note: SessionLocal já é uma fábrica de sessões configurada com um engine.
    # Se precisarmos de um async_sessionmaker, vizu_db_connector precisará ser atualizado.
    return SessionLocal


def get_redis_async_client(
    settings: Settings = Depends(get_app_settings)
) -> AsyncRedis:
    """
    Retorna um cliente Redis assíncrono.
    """
    # TODO: Implementar a criação de um cliente Redis assíncrono com base em settings.REDIS_URL
    # Por enquanto, retornamos um mock ou um cliente básico.
    logger.warning("Usando cliente Redis assíncrono mockado/básico. Implementar criação real com REDIS_URL.")
    return AsyncRedis(host='localhost', port=6379, db=0) # Placeholder


def get_redis_service(
    redis_client: AsyncRedis = Depends(get_redis_async_client)
) -> RedisService:
    """
    Retorna o serviço de Redis (wrapper em volta do cliente).
    """
    return RedisService(redis_client)


def get_context_service(
    db_session_factory: SessionLocal = Depends(get_db_session_factory),
    redis_service: RedisService = Depends(get_redis_service)
) -> ContextService:
    """
    Retorna o serviço de Contexto, injetando suas dependências (DB e Redis).
    Este é o serviço que o MCP usará para buscar o VizuClientContext.
    """
    # Cria uma sessão síncrona a partir da fábrica para o ContextService
    db_session = db_session_factory()
    try:
        return ContextService(
            db_session=db_session,
            cache_service=redis_service
        )
    finally:
        db_session.close() # Garante que a sessão seja fechada após o uso

# --- Singletons Globais (para uso direto onde a injeção não é possível/prática) ---
# Estes são os singletons que o MCP pode precisar acessar diretamente.
# Eles dependem das funções de injeção acima.

# O singleton do ContextService é o mais importante para o MCP.
# Não inicializamos mais em nível de módulo para permitir mocking em testes.

logger.info("Todas as dependências globais foram inicializadas.")


# --- Funções de Injeção (Opcional, mas boa prática) ---
# Embora possamos importar os singletons diretamente,
# criar 'getters' nos prepara para injeção de dependência futura.

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependência do FastAPI/MCP para obter uma sessão de DB (se necessário)."""
    # Esta função agora usa a db_session_factory obtida via injeção.
    # Se db_session_factory for síncrona, isso precisará ser adaptado.
    # Por enquanto, assume que SessionLocal pode ser usada em um contexto async.
    async with db_session_factory() as session:
        yield session


# get_context_service já está definido acima.