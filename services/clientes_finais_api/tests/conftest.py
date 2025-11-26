import pytest
import os
os.environ['OTEL_SDK_DISABLED'] = 'true'

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import create_database, database_exists, drop_database

# 1. Importa a FACTORY da aplicação
from clientes_finais_api.main import create_app

# 2. Importa as dependências que serão sobrescritas
from clientes_finais_api.core.config import Settings, get_settings
from vizu_db_connector.core import get_db
from vizu_models import Base

TEST_DATABASE_URL = "postgresql://user:password@localhost:5433/vizu_db_test"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def db_session_scope():
    """Cria e destrói o banco de dados de teste uma única vez por sessão."""
    if database_exists(engine.url):
        drop_database(engine.url)
    create_database(engine.url)
    Base.metadata.create_all(bind=engine)
    yield
    drop_database(engine.url)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Fornece uma transação de banco de dados isolada para cada teste."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def api_client(db_session: Session) -> TestClient:
    """
    Cria um TestClient com configuração e banco de dados totalmente isolados.
    """
    # Define a variável de ambiente para DESABILITAR completamente o SDK da telemetria
    os.environ['OTEL_SDK_DISABLED'] = 'true'

    # Funções que definem o comportamento das dependências durante os testes
    def get_test_settings() -> Settings:
        return Settings(
            DATABASE_URL=TEST_DATABASE_URL,
            OTEL_EXPORTER_OTLP_ENDPOINT=None
        )

    def override_get_db():
        """Fornece a sessão de banco de dados do teste."""
        yield db_session

    app = create_app()
    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client