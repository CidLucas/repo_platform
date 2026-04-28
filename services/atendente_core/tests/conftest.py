# tests/conftest.py
"""
Test fixtures for atendente_core.

Note: Tests require PostgreSQL (for JSONB support). By default uses local Docker postgres.
Set TEST_DATABASE_URL to override.
"""

import os

import pytest

# Set environment variables before any imports that might use them
os.environ["LANGCHAIN_API_KEY"] = "test_api_key"
os.environ["TWILIO_AUTH_TOKEN"] = "test_auth_token"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
# Use PostgreSQL for tests (required for JSONB columns)
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/blu_db"
)
os.environ["LANGCHAIN_PROJECT"] = "dev-tests"
os.environ["LLM_PROVIDER"] = "ollama_cloud"

# Now we can safely import the app and other dependencies
import fakeredis
from atendente_core.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from blu_context_service.dependencies import get_redis_service
from blu_context_service.redis_service import RedisService


# Since we're setting envs at module level, this fixture can be used for other setups
@pytest.fixture(scope="session", autouse=True)
def mock_settings_env_vars():
    """
    Additional test environment setup if needed.
    Basic env vars are already set at module level.
    """
    os.environ["LANGCHAIN_API_KEY"] = "test_api_key"
    os.environ["TWILIO_AUTH_TOKEN"] = "test_auth_token"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["DATABASE_URL"] = os.getenv(
        "TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/blu_db"
    )
    os.environ["LANGCHAIN_PROJECT"] = "dev-tests"
    os.environ["LLM_PROVIDER"] = "ollama_cloud"
    os.environ["OTEL_SDK_DISABLED"] = "true"


# Poetry gerencia o path via dependências em pyproject.toml

# Importa APÓS a configuração do path e das variáveis de ambiente


# --- Fixtures de Banco de Dados e Cliente de Teste ---


@pytest.fixture(scope="session")
def db_engine():
    """Cria uma engine de banco de dados única para a sessão de testes."""
    engine = create_engine(os.environ["DATABASE_URL"])
    # Don't create tables - use existing schema from migrations
    # Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def test_client():
    """
    Configura o TestClient com as dependências mockadas.
    """
    fake_redis_client = fakeredis.FakeStrictRedis()
    fake_redis_service = RedisService(fake_redis_client)

    def override_get_redis_service():
        yield fake_redis_service

    app.dependency_overrides[get_redis_service] = override_get_redis_service

    with TestClient(app) as client:
        yield client, fake_redis_client

    app.dependency_overrides.clear()
