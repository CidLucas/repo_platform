# services/clients_api/tests/conftest.py (VERSÃO CORRIGIDA E FINAL)
import sys
from pathlib import Path

# --- INÍCIO DA CORREÇÃO DE PATH ---
# Esta é a correção crucial. Ela força o Python a enxergar as bibliotecas locais.
# 1. Encontra o diretório raiz do projeto (vizu-mono) subindo na árvore de pastas.
project_root = Path(__file__).resolve().parents[3]

# 2. Adiciona o diretório 'src' de cada biblioteca compartilhada ao sys.path.
#    Isso deve ser feito ANTES de qualquer importação da aplicação.
libs_path = project_root / "libs"
sys.path.insert(0, str(libs_path / "vizu_models" / "src"))
sys.path.insert(0, str(libs_path / "vizu_db_connector" / "src"))
# --- FIM DA CORREÇÃO DE PATH ---

# Agora que o path está corrigido, podemos importar com segurança.
import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import create_database, database_exists, drop_database

from clients_api.main import create_app
from clients_api.api.dependencies import get_db_session
from vizu_models import Base

# --- Configuração do Banco de Dados de Teste ---
TEST_DATABASE_URL = "postgresql://user:password@localhost:5433/vizu_clients_api_test"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Fixtures do Pytest (sem alterações) ---


@pytest.fixture(scope="session", autouse=True)
def db_session_scope():
    os.environ["OTEL_SDK_DISABLED"] = "true"
    if database_exists(engine.url):
        drop_database(engine.url)
    create_database(engine.url)
    Base.metadata.create_all(bind=engine)
    yield
    drop_database(engine.url)


@pytest.fixture(scope="function")
def db_session() -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as client:
        yield client
