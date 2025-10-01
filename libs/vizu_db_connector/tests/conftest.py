import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Importamos nossa Base, que conhece todas as nossas tabelas
from vizu_db_connector.models.base import Base

# Usa uma variável de ambiente para o DB de teste, com um fallback
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/vizu_db_test")

@pytest.fixture(scope="session")
def engine():
    """Cria uma única engine para toda a sessão de testes."""
    return create_engine(TEST_DATABASE_URL)

@pytest.fixture(scope="session", autouse=True)
def create_tables(engine):
    """
    Fixture principal de setup: cria todas as tabelas no início dos testes
    e as remove no final. `autouse=True` garante que ela sempre execute.
    """
    # Remove qualquer resquício de tabelas antigas
    Base.metadata.drop_all(engine)
    # Cria todas as tabelas que herdam da nossa Base
    Base.metadata.create_all(engine)
    yield
    # Limpeza: remove todas as tabelas ao final da sessão de testes
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, create_tables) -> Session:
    """
    Fornece uma sessão de banco de dados limpa para cada teste,
    usando um padrão de transação com rollback para isolar os testes.
    """
    connection = engine.connect()
    # Inicia uma transação "externa"
    transaction = connection.begin()
    # Cria uma sessão ligada a essa transação
    session = sessionmaker(bind=connection)()

    yield session

    # Ao final do teste, fecha a sessão e desfaz a transação.
    # Isso garante que cada teste comece com o banco de dados limpo.
    session.close()
    transaction.rollback()
    connection.close()