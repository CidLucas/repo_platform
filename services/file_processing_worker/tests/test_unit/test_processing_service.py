import io
import json
from unittest.mock import MagicMock

import pytest
from file_processing_worker.core.config import Settings
from file_processing_worker.parsers.base_parser import BaseParser

# O que estamos a testar (System Under Test - SUT)
from file_processing_worker.services.processing_service import ProcessingService

# As dependências que vamos mockar
from file_processing_worker.services.routing_service import RoutingService
from pytest_mock import MockerFixture

# --- Fixture Local (Específica para este teste) ---


@pytest.fixture
def mock_routing_service(mocker: MockerFixture) -> MagicMock:
    """
    Cria um mock para o RoutingService.
    Este mock já inclui um mock do 'BaseParser' no seu retorno.
    """

    # 1. Mockar o parser que o roteador deve retornar
    mock_parser = mocker.MagicMock(spec=BaseParser)
    mock_parser.parse.return_value = "Texto extraído com sucesso pelo mock parser"

    # 2. Mockar o RoutingService
    mock_router = mocker.MagicMock(spec=RoutingService)
    mock_router.get_parser.return_value = mock_parser

    return mock_router


# --- O Teste Unitário ---


def test_process_message_success(
    settings: Settings,
    mock_storage_client: MagicMock,  # Fixture do conftest.py
    mock_routing_service: MagicMock,  # Fixture local
    mocker: MockerFixture,
):
    """
    Testa o fluxo de sucesso completo do ProcessingService,
    verificando GCS -> Routing -> Parsing.
    """
    # --- 1. Arrange (Preparação) ---

    # Instancia o serviço principal (SUT), injetando os mocks
    service = ProcessingService(
        storage_client=mock_storage_client,
        routing_service=mock_routing_service,
        settings=settings,
    )

    # Configurar o mock do GCS (do conftest)
    downloaded_content = b"conteudo fake do ficheiro"

    def mock_download_effect(file_stream: io.BytesIO):
        file_stream.write(downloaded_content)
        file_stream.seek(0)

    # [CORRETO] Aceder aos mocks internos sem os chamar
    mock_bucket = mock_storage_client.get_bucket.return_value
    mock_blob = mock_bucket.blob.return_value

    # Configurar o mock_blob (que já existe)
    mock_blob.download_to_file.side_effect = mock_download_effect

    # Criar a mensagem Pub/Sub (payload)
    message_payload = {
        "job_id": "job-123",
        "client_id": "client-456",
        "gcs_path": "client-456/job-123-teste.pdf",
        "original_filename": "teste.pdf",
        "content_type": "application/pdf",
        "trace_id": "trace-789",
    }
    message_bytes = json.dumps(message_payload).encode("utf-8")

    # --- 2. Act (Execução) ---

    # Chamar o método principal do serviço
    service.process_message(message_bytes)

    # --- 3. Assert (Verificação) ---

    # 3.1. Verificação do GCS (Download)
    mock_storage_client.get_bucket.assert_called_with("test-bucket")
    mock_storage_client.get_bucket().blob.assert_called_with(
        "client-456/job-123-teste.pdf"
    )
    mock_blob.download_to_file.assert_called_once()  # Verifica se o download ocorreu

    # 3.2. Verificação do Roteamento
    mock_routing_service.get_parser.assert_called_with("application/pdf")

    # 3.3. Verificação do Parser
    # Pega a instância do parser que o mock_router retornou
    mock_parser_instance = mock_routing_service.get_parser()

    # Verifica se o método 'parse' foi chamado
    mock_parser_instance.parse.assert_called_once()
