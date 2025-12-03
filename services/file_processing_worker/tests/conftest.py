import pytest
import io
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from google.cloud import storage

# Importações da nossa aplicação
from file_processing_worker.main import create_app
from file_processing_worker.core.config import Settings, get_settings
from file_processing_worker.core.worker import get_gcp_storage_client

# --- Fixture 1: Configurações de Teste ---


@pytest.fixture
def settings(monkeypatch):
    """
    Fornece uma instância de Settings com valores de teste controlados.
    Desativa a telemetria (OTEL) para não poluir os testes.
    """
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")  # Desativa OTEL
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PUBSUB_SUBSCRIPTION_ID", "test-sub")

    get_settings.cache_clear()
    return get_settings()


# --- Fixture 2: Mock do GCS (Testes Unitários e de Integração) ---


@pytest.fixture
def mock_storage_client(mocker: MagicMock) -> MagicMock:
    """
    Cria um mock detalhado do storage.Client do GCS.
    Configurado para simular o download de um ficheiro.
    """
    mock_blob = mocker.MagicMock()
    mock_blob.exists.return_value = True

    # Esta é a parte importante: simular o 'download_to_file'
    # Usamos 'side_effect' para escrever bytes no stream que o teste passa.
    def mock_download(file_stream: io.BytesIO):
        file_stream.write(b"dummy file content")
        file_stream.seek(0)

    mock_blob.download_to_file = MagicMock(side_effect=mock_download)

    mock_bucket = mocker.MagicMock()
    mock_bucket.blob.return_value = mock_blob

    mock_client = mocker.MagicMock(spec=storage.Client)
    mock_client.get_bucket.return_value = mock_bucket

    return mock_client


# --- Fixture 3: Cliente HTTP (Testes de Integração) ---


@pytest.fixture
def client(
    settings: Settings,
    mock_storage_client: MagicMock,
):
    """
    Cria um TestClient do FastAPI para testes de integração.

    Substitui a dependência real do GCS pelo nosso mock.
    """

    # 1. Cria a aplicação real
    app = create_app()

    # 2. Substitui as dependências
    app.dependency_overrides[get_gcp_storage_client] = lambda: mock_storage_client
    app.dependency_overrides[get_settings] = lambda: settings

    # 3. Cria o cliente de teste HTTP
    with TestClient(app) as test_client:
        yield test_client

    # 4. Limpa os overrides
    app.dependency_overrides.clear()
