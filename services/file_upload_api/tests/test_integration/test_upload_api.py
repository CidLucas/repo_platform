import io
import json
import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


# O 'client' vem do conftest.py
# O 'mocker' é um fixture do pytest-mock
def test_upload_file_success(
    client: TestClient,
    mocker: MagicMock,
    mock_storage_client: MagicMock,
    mock_publisher_client: MagicMock,
):
    """
    Testa a integração do endpoint POST /v1/upload.
    Verifica se a API responde corretamente e se os serviços
    (GCS e Pub/Sub) são chamados pela camada de serviço.
    """
    # --- 1. Arrange (Preparação) ---

    # Conteúdo do arquivo falso
    file_content = b"dados do meu arquivo de teste"
    file_name = "arquivo_integracao.txt"
    content_type = "text/plain"

    # Criamos o 'files' no formato multipart/form-data
    # (nome_do_campo, (nome_arquivo, conteudo, content_type))
    mock_file = {"file": (file_name, io.BytesIO(file_content), content_type)}

    # Mockar UUID e Trace ID para garantir uma resposta determinística
    # (mesmo que o service.py já tenha mocks, é bom garantir no teste de integração)
    test_job_id = uuid.UUID("abcdef12-1234-5678-1234-567812345678")
    mocker.patch(
        "file_upload_api.services.upload_service.uuid.uuid4", return_value=test_job_id
    )
    mocker.patch(
        "file_upload_api.services.upload_service.UploadService._get_current_trace_id",
        return_value="integration-test-trace-id",
    )

    # O cliente (DUMMY_CLIENTE_VIZU_ID) é mockado em dependencies.py
    expected_cliente_id_str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

    # --- 2. Act (Execução) ---

    # Faz a chamada HTTP POST real para a API em memória
    response = client.post("/v1/upload", files=mock_file)

    # --- 3. Assert (Verificação) ---

    # 3.1. Verificar a Resposta HTTP
    assert response.status_code == 201

    json_response = response.json()
    expected_gcs_path = f"{expected_cliente_id_str}/{test_job_id}-{file_name}"

    assert json_response["job_id"] == str(test_job_id)
    assert json_response["file_name"] == file_name
    assert json_response["content_type"] == content_type
    assert json_response["gcs_path"] == expected_gcs_path

    # 3.2. Verificar Mocks (Confirma que o serviço foi chamado corretamente)

    # Verificar GCS (através do mock injetado no 'client')
    mock_storage_client.get_bucket("test-bucket").blob(
        expected_gcs_path
    ).upload_from_file.assert_called_once()

    # Verificar Pub/Sub (através do mock injetado no 'client')
    expected_payload = {
        "job_id": str(test_job_id),
        "cliente_vizu_id": expected_cliente_id_str,
        "gcs_path": expected_gcs_path,
        "original_filename": file_name,
        "content_type": content_type,
        "trace_id": "integration-test-trace-id",
    }
    expected_data = json.dumps(expected_payload).encode("utf-8")

    mock_publisher_client.publish.assert_called_with(
        "projects/test-project/topics/test-topic",
        expected_data,  # <-- Alterado de 'data=expected_data' para posicional
    )
