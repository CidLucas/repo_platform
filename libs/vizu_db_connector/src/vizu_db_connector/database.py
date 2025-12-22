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
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Cannot create database engine."
            )
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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
