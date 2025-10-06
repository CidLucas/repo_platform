# tests/conftest.py

import sys
import os
import pytest
import fakeredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# --- Fixture de Setup do Ambiente (Executa Primeiro) ---
@pytest.fixture(scope="session", autouse=True)
def mock_settings_env_vars():
    """
    Usa os.environ para definir variáveis de ambiente para toda a sessão de teste.
    - scope='session' e autouse=True garantem que isso execute antes de qualquer outra coisa.
    """
    os.environ["LANGCHAIN_API_KEY"] = "test_api_key"
    os.environ["TWILIO_AUTH_TOKEN"] = "test_auth_token"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["LANGCHAIN_PROJECT"] = "dev-tests"

# --- Bloco de Configuração de Path ---
# Deve vir depois da fixture de ambiente para garantir que as variáveis existam
# no momento em que os módulos da aplicação são importados.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
libs_path = os.path.abspath(os.path.join(project_root, '../../libs'))
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# Importa APÓS a configuração do path e das variáveis de ambiente
from atendente_api.main import app
from atendente_api.api.routes import validate_twilio_request
from atendente_api.services.redis_service import get_redis_service, RedisService
from vizu_db_connector.core import get_db
from vizu_db_connector.models.base import Base


# --- Fixtures de Banco de Dados e Cliente de Teste ---

@pytest.fixture(scope="session")
def db_engine():
    """Cria uma engine de banco de dados única para a sessão de testes."""
    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def test_client_db_session(db_engine):
    """
    Gerencia a sessão e a transação do banco de dados para cada teste,
    garantindo que a aplicação use a mesma sessão.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    connection = db_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_client(test_client_db_session):
    """
    Configura o TestClient com as dependências mockadas.
    """
    fake_redis_client = fakeredis.FakeStrictRedis()
    fake_redis_service = RedisService(fake_redis_client)

    def override_validate_twilio_request(): pass
    def override_get_redis_service(): yield fake_redis_service

    app.dependency_overrides[validate_twilio_request] = override_validate_twilio_request
    app.dependency_overrides[get_redis_service] = override_get_redis_service

    with TestClient(app) as client:
        yield client, fake_redis_client

    app.dependency_overrides.clear()