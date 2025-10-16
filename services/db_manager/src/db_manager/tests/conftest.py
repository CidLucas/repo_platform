# services/db_manager/tests/conftest.py
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database, drop_database

@pytest.fixture(scope="session")
def db_url():
    """Retorna a URL do banco de dados de teste, lida do ambiente."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL não está definida. Exporte a variável de ambiente.")
    return url

@pytest.fixture(scope="session")
def test_db_engine(db_url):
    """Cria e destrói o banco de dados de teste para a sessão."""
    if database_exists(db_url):
        drop_database(db_url)

    create_database(db_url)
    engine = create_engine(db_url)

    yield engine

    engine.dispose()
    drop_database(db_url)

@pytest.fixture
def db_session(test_db_engine):
    """Fornece uma sessão de banco de dados para um teste."""
    connection = test_db_engine.connect()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    connection.close()