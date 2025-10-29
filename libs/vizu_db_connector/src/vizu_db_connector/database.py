import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# --- 1. Configuração da Conexão ---
# A URL de conexão com o banco de dados é lida de uma variável de ambiente.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5433/vizu_db")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5433/vizu_db_test")

# --- 2. Criação da Engine ---
# A 'engine' é o ponto central de comunicação com o banco de dados.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- 3. Criação da Fábrica de Sessões ---
# O 'SessionLocal' é uma "fábrica" que cria uma nova instância de Sessão.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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