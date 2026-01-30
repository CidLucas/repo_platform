import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Nao apague, password do supabase tMz1us7KsAHQs6QT
# --- 1. Configuração da Conexão ---
# A URL de conexão com o banco de dados é lida de uma variável de ambiente.
DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://user:password@localhost:5432/vizu_db_test",
)

# --- 2. Lazy Engine Initialization ---
# The engine and SessionLocal are created lazily to avoid errors when DATABASE_URL is not set
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine.

    Connection pool settings optimized for Supabase pooler:
    - pool_size: Max persistent connections (keep low for Supabase Session mode)
    - max_overflow: Additional connections allowed temporarily
    - pool_timeout: Seconds to wait for a connection from pool
    - pool_recycle: Recycle connections after N seconds (prevents stale connections)
    - pool_pre_ping: Test connections before use (handles dropped connections)

    NOTE: Supabase PgBouncer may drop idle connections after ~60s.
    We use aggressive pool_recycle to prevent SSL disconnection errors.

    IMPORTANT: Connection pool is shared across all users of vizu_db_connector.
    Each service should ensure connections are properly returned to pool via:
    - Using context managers: `with session:` or `with PostgresRepository():`
    - FastAPI dependencies with yield pattern (generator)
    - Explicit .close() calls in finally blocks
    """
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Cannot create database engine."
            )
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,   # CRITICAL: Test connection before use
            pool_size=5,          # Increased from 3 - allows more concurrent requests
            max_overflow=10,      # Allow burst up to 15 total connections (was 7)
            pool_timeout=30,      # Wait up to 30s for a connection
            pool_recycle=180,     # Recycle every 3 min (was 5 min - more aggressive for Supabase)
            # echo_pool="debug",  # Disabled - enable for pool debugging only
        )
    return _engine


def SessionLocal():
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()


# --- 4. Função de Dependência para FastAPI ---
# SUGESTÃO: Renomear para 'get_db_session' para maior clareza.
def get_db_session() -> Generator[Session, None, None]:
    """
    Gerencia o ciclo de vida de uma sessão do banco de dados para FastAPI.
    - Cria uma sessão para uma requisição.
    - Disponibiliza a sessão (yield).
    - Garante que a sessão seja sempre fechada ao final.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
