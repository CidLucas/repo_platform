import io
import json
import uuid
from unittest.mock import MagicMock

from fastapi import UploadFile
from pytest_mock import MockerFixture

# Componentes que estamos a testar
from file_upload_api.services.upload_service import UploadService
from file_upload_api.schemas.upload_schemas import FileUploadResponse
from file_upload_api.core.config import Settings

# Padrão Vizu: Testar a lógica de serviço isoladamente
def test_process_upload_success(
    settings: Settings,
    mock_storage_client: MagicMock,
    mock_publisher_client: MagicMock,
    mocker: MockerFixture,
):
    """
    Testa o fluxo de sucesso completo do UploadService,
    verificando se o GCS e o Pub/Sub são chamados corretamente.
    """
    # --- 1. Arrange (Preparação) ---

    # Criar o serviço sob teste, injetando os mocks do conftest
    service = UploadService(
        storage_client=mock_storage_client,
        publisher_client=mock_publisher_client,
        settings=settings,
    )

    # Simular os dados de entrada
    cliente_id = uuid.uuid4()
    mock_file_content = b"Este e um arquivo de teste"

    # Criar um UploadFile mockado
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "teste.txt"
    mock_file.content_type = "text/plain"
    mock_file.file = io.BytesIO(mock_file_content)

    # Mockar funções que geram valores aleatórios (Padrão: Teste Determinístico)
    test_job_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    mocker.patch("file_upload_api.services.upload_service.uuid.uuid4", return_value=test_job_id)

    test_trace_id = "mock-trace-id-abc"
    mocker.patch(
        "file_upload_api.services.upload_service.UploadService._get_current_trace_id",
        return_value=test_trace_id,
    )

    # --- 2. Act (Execução) ---

    response = service.process_upload(file=mock_file, cliente_vizu_id=cliente_id)

    # --- 3. Assert (Verificação) ---

    # 3.1. Verificar a resposta da API
    assert isinstance(response, FileUploadResponse)
    assert response.job_id == test_job_id
    assert response.file_name == "teste.txt"

    # 3.2. Verificar chamada ao GCS (Storage)
    expected_gcs_path = f"{cliente_id}/{test_job_id}-teste.txt"
    assert response.gcs_path == expected_gcs_path

    # Verifica a cadeia de chamadas no mock do GCS
    mock_storage_client.get_bucket.assert_called_with("test-bucket")
    mock_storage_client.get_bucket().blob.assert_called_with(expected_gcs_path)
    mock_storage_client.get_bucket().blob().upload_from_file.assert_called_with(
        mock_file.file
    )

    # 3.3. Verificar chamada ao Pub/Sub

    # O path do tópico deve ser construído corretamente
    mock_publisher_client.topic_path.assert_called_with("test-project", "test-topic")

    # O payload da mensagem deve ser serializado corretamente
    expected_payload = {
        "job_id": str(test_job_id),
        "cliente_vizu_id": str(cliente_id),
        "gcs_path": expected_gcs_path,
        "original_filename": "teste.txt",
        "content_type": "text/plain",
        "trace_id": test_trace_id, # Padrão Vizu: Observabilidade
    }
    expected_data = json.dumps(expected_payload).encode("utf-8")

    # A chamada de publicação deve ter o tópico e o payload corretos
    mock_publisher_client.publish.assert_called_with(
        "projects/test-project/topics/test-topic",
        expected_data # <-- Alterado de 'data=expected_data' para posicional
    )