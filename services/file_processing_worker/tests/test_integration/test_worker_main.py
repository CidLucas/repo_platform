import json
import base64
import io
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# As fixtures 'client' e 'mock_storage_client' vêm do conftest.py
def test_pubsub_push_integration_success(
    client: TestClient,
    mock_storage_client: MagicMock,
    mocker: MagicMock
):
    """
    Testa a integração do endpoint POST / (Pub/Sub Push).
    Verifica se a API recebe a mensagem, descodifica, e chama
    o ProcessingService, que por sua vez chama o GCS.
    """
    # --- 1. Arrange (Preparação) ---

    # 1.1. Configurar o mock do GCS (definido no conftest)
    pdf_content = b"%PDF-1.4...fake pdf content..."

    def mock_download_effect(file_stream: io.BytesIO):
        file_stream.write(pdf_content)
        file_stream.seek(0)

    # [CORRETO] Aceder aos mocks internos sem os chamar
    mock_bucket = mock_storage_client.get_bucket.return_value
    mock_blob = mock_bucket.blob.return_value

    # Configurar o mock_blob (que já existe)
    mock_blob.download_to_file.side_effect = mock_download_effect

    # 1.2. Mockar o parser de PDF (para isolar o teste do parser em si)
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse.return_value = "Texto extraído do PDF"

    # Mockamos a *classe* PDFParser
    mock_pdf_parser_class = mocker.patch(
        "file_processing_worker.services.routing_service.PDFParser"
    )

    # CORREÇÃO: Damos um __name__ ao mock da CLASSE (para o log funcionar)
    mock_pdf_parser_class.__name__ = "MockPDFParser"

    # Configuramos o mock da CLASSE para retornar a INSTÂNCIA mockada
    mock_pdf_parser_class.return_value = mock_parser_instance

    # 1.3. Criar a mensagem Pub/Sub (a ser codificada)
    message_payload = {
        "job_id": "job-integration-test",
        "cliente_vizu_id": "client-abc",
        "gcs_path": "client-abc/job-integration-test.pdf",
        "original_filename": "teste.pdf",
        "content_type": "application/pdf", # Importante para o RoutingService
        "trace_id": "trace-integration",
    }
    message_bytes = json.dumps(message_payload).encode("utf-8")

    # 1.4. Codificar para Base64 (como o Pub/Sub faz)
    message_data_base64 = base64.b64encode(message_bytes).decode("utf-8")

    # 1.5. Criar o 'envelope' completo do Pub/Sub Push
    pubsub_push_payload = {
        "subscription": "projects/test-project/subscriptions/test-sub",
        "message": {
            "data": message_data_base64,
            "message_id": "msg-id-123",
            "attributes": {}
        }
    }

    # --- 2. Act (Execução) ---

    # Fazer a chamada HTTP POST simulando o Pub/Sub
    response = client.post("/", json=pubsub_push_payload)

    # --- 3. Assert (Verificação) ---

    # 3.1. Verificar Resposta HTTP (ACK para o Pub/Sub)
    assert response.status_code == 204 # HTTP 204 No Content

    # 3.2. Verificar Mock do GCS (Download)
    # O ProcessingService foi chamado e tentou descarregar o ficheiro
    mock_storage_client.get_bucket.assert_called_with("test-bucket")
    mock_storage_client.get_bucket().blob.assert_called_with(
        "client-abc/job-integration-test.pdf"
    )
    mock_blob.download_to_file.assert_called_once()

    # 3.3. Verificar Mock do Parser
    # O RoutingService funcionou e o parser correto foi chamado
    mock_parser_instance.parse.assert_called_once()