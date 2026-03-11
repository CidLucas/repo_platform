import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ============================================================================
# ENGINE COMPARTILHADA (SINGLETON)
# ============================================================================
# Uma única engine para todos os clientes. O isolamento é garantido pelo RLS.
#
# NOTA: Este módulo usa SQLAlchemy porque o LangChain SQL Agent requer
# uma conexão direta ao PostgreSQL para introspecção e execução de queries.
#
# Para operações CRUD simples, use vizu_supabase_client que usa a API REST
# do Supabase e não tem problemas de DNS/conectividade.
#
# Ambientes:
# - LOCAL: DATABASE_URL postgresql://user:password@localhost:5432/vizu_db
# - DOCKER: DATABASE_URL postgresql://user:password@postgres:5432/vizu_db
# - SUPABASE: Requer conexão direta (pode ter issues de DNS)

_shared_engine: Engine | None = None


def _get_database_url() -> str:
    """
    Obtém a URL de conexão do banco de dados.

    Prioridade:
    1. DATABASE_URL (conexão direta PostgreSQL)
    2. Construção a partir de variáveis POSTGRES_*

    Para Supabase, se houver problemas de DNS com a URL direta,
    considere usar o Supabase SDK para CRUD e reservar SQLAlchemy
    apenas para o SQL Agent em ambiente local/Docker.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Fallback: construir a URL a partir de variáveis individuais
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_name = os.getenv("POSTGRES_DB", "postgres")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


def get_shared_engine() -> Engine:
    """
    Retorna a engine compartilhada (singleton).
    Cria a engine na primeira chamada.

    NOTE: Pool settings are conservative to avoid exhausting Supabase connections
    when combined with vizu_db_connector pools from other services.
    Total Supabase connection limit is typically 60 for Session mode.
    """
    global _shared_engine

    if _shared_engine is None:
        db_url = _get_database_url()
        logger.info("Criando engine SQL compartilhada...")

        _shared_engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,       # Reduced from 10 - share Supabase slots with other services
            max_overflow=10,   # Reduced from 20 - prevents pool exhaustion
            pool_recycle=180,  # Recycle every 3 min (was 5 min - more aggressive for Supabase)
            pool_pre_ping=True,  # Verifica conexão antes de usar
            pool_timeout=30,   # Wait up to 30s for connection (fail fast)
            echo=False,  # Desabilita log de queries (usar logging próprio)
        )

        logger.info("Engine SQL compartilhada criada com sucesso.")

    return _shared_engine


def close_shared_engine() -> None:
    """Fecha a engine compartilhada (para shutdown graceful)."""
    global _shared_engine
    if _shared_engine:
        _shared_engine.dispose()
        _shared_engine = None
        logger.info("Engine SQL compartilhada fechada.")
