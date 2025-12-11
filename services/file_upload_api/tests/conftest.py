from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from file_upload_api.api.router import (
    get_gcp_publisher_client,
    get_gcp_storage_client,
)
from file_upload_api.core.config import Settings, get_settings

# Importações da nossa aplicação
from file_upload_api.main import create_app
from google.cloud import storage
from google.cloud.pubsub_v1 import PublisherClient

# --- Fixture 1: Configurações de Teste (Padrão Vizu: Agnóstico) ---


@pytest.fixture  # Removido o 'scope="session"'
def settings(monkeypatch):  # Corrigido para 'monkeypatch'
    """
    Fornece uma instância de Settings com valores de teste controlados.
    Desativa a telemetria (OTEL) para não poluir os testes.
    """
    # Garante que as variáveis de ambiente de teste sejam usadas
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")  # Desativa OTEL
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PUBSUB_TOPIC_ID", "test-topic")

    # Força o 'get_settings' a recarregar com as novas variáveis
    get_settings.cache_clear()
    return get_settings()


# --- Fixtures 2 & 3: Mocks para Testes Unitários (Padrão Vizu: Testabilidade) ---


@pytest.fixture
def mock_storage_client(mocker: MagicMock) -> MagicMock:
    """
    Cria um mock detalhado do storage.Client do GCS.
    Isso é usado em testes unitários para simular o upload.
    """
    # Criamos mocks internos para a cadeia de chamadas:
    # client.get_bucket(...) -> bucket
    # bucket.blob(...) -> blob
    # blob.upload_from_file(...)
    mock_blob = mocker.MagicMock()
    mock_bucket = mocker.MagicMock()

    mock_bucket.blob.return_value = mock_blob

    mock_client = mocker.MagicMock(spec=storage.Client)
    mock_client.get_bucket.return_value = mock_bucket

    return mock_client


@pytest.fixture
def mock_publisher_client(mocker: MagicMock) -> MagicMock:
    """
    Cria um mock detalhado do PublisherClient do Pub/Sub.
    Isso é usado em testes unitários para simular a publicação.
    """
    mock_client = mocker.MagicMock(spec=PublisherClient)

    # Configura o mock para retornar o 'topic_path' esperado
    mock_client.topic_path.return_value = "projects/test-project/topics/test-topic"

    # Configura o mock do 'publish' para retornar um "Future" mockado
    mock_future = mocker.MagicMock()
    mock_future.result.return_value = "mock-message-id-123"  # Simula o ID da msg
    mock_client.publish.return_value = mock_future

    return mock_client


# --- Fixture 4: Cliente HTTP para Testes de Integração ---


@pytest.fixture
def client(
    settings: Settings,  # Usa a fixture de settings
    mock_storage_client: MagicMock,
    mock_publisher_client: MagicMock,
):
    """
    Cria um TestClient do FastAPI para testes de integração.

    Crucial: Ele substitui (overrides) as dependências da API
    para usar nossos mocks, isolando o teste de serviços externos.
    """

    # 1. Cria a aplicação real
    app = create_app()

    # 2. Substitui as dependências reais pelas mockadas
    app.dependency_overrides[get_gcp_storage_client] = lambda: mock_storage_client
    app.dependency_overrides[get_gcp_publisher_client] = lambda: mock_publisher_client
    app.dependency_overrides[get_settings] = lambda: settings

    # 3. Cria o cliente de teste HTTP
    with TestClient(app) as test_client:
        yield test_client  # O teste executa aqui

    # 4. Limpa os overrides após o teste
    app.dependency_overrides.clear()
