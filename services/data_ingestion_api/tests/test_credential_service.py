# services/data_ingestion_api/tests/test_credential_service.py

from unittest.mock import AsyncMock

import pytest

# Corrija as importações internas para usar o caminho do arquivo (sem o nome do pacote):
from data_ingestion_api.schemas.schemas import (
    BigQueryCredentialCreate,
)
from data_ingestion_api.services.credential_service import CredentialService
from pydantic import ValidationError


# Fixture auxiliar para dados de payload
@pytest.fixture
def bigquery_payload():
    service_account_data = {
        "type": "service_account",
        "private_key_id": "fake-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----FAKE-----END PRIVATE KEY-----\n",
        "client_email": "vizu-connector@gcp.iam.gserviceaccount.com",
        "client_id": "1234567890",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return BigQueryCredentialCreate(
        cliente_vizu_id="vizu-cliente-a",
        nome_conexao="BQ Dados Financeiros",
        tipo_servico="BIGQUERY",
        project_id="projeto-cliente-a-prod",
        service_account_json=service_account_data
    )

# Fixture que será injetada em todos os testes
@pytest.fixture
def mock_credential_service(mocker):
    """Cria uma instância do CredentialService com mocks para Secret Manager e DB."""

    # 1. Mock do Secret Manager (Simula o envio e retorno do Secret ID)
    mock_store_secret = mocker.patch(
        'data_ingestion_api.services.credential_service.secret_manager.store_secret',
        new_callable=AsyncMock
    )
    mock_store_secret.return_value = "vizu-prod-secret-id-gcp-12345"

    # 2. Mock do Supabase Client (Simula a persistência do Secret ID)
    mock_save_ref = mocker.patch(
        'data_ingestion_api.services.supabase_client.insert',
        new_callable=AsyncMock
    )
    mock_save_ref.return_value = {
        "id": "db-uuid-001",
        "cliente_vizu_id": "vizu-cliente-a",
        "nome_servico": "BigQuery Teste",
        "credenciais_cifradas": "vizu-prod-secret-id-gcp-12345"
    }

    # 3. Mock do Rollback (delete_secret) - NOVO
    mock_delete_secret = mocker.patch(
        'data_ingestion_api.services.credential_service.secret_manager.delete_secret',
        new_callable=AsyncMock
    )
    mock_delete_secret.return_value = True # Sucesso no rollback

    # Instancia o serviço com os mocks
    service = CredentialService()

    return service, mock_store_secret, mock_save_ref, mock_delete_secret


@pytest.mark.asyncio
async def test_create_bigquery_credential_success(mock_credential_service, bigquery_payload):
    """
    Testa o fluxo completo de criação de credenciais BigQuery.
    CRÍTICO: Garante que a senha (service_account_json) NÃO é enviada ao DB.
    """

    # Desempacota QUATRO mocks
    service, mock_store_secret, mock_save_ref, mock_delete_secret = mock_credential_service

    # 2. Executa a função
    response = await service.create_credential(bigquery_payload)

    # 3. Assertions (Verificação de Segurança e Fluxo)

    # A) SEGURANÇA: Verifica se a Service Account Key foi enviada ao Secret Manager
    mock_store_secret.assert_called_once()

    # B) INTEGRIDADE: Verifica se o Secret ID foi retornado e persistido
    assert response.secret_manager_id == "vizu-prod-secret-id-gcp-12345"
    assert response.status == "PENDENTE_VALIDACAO"

    # C) CRÍTICO (VIZU CORE): Garante que a Service Account Key NUNCA foi enviada ao Supabase
    db_call_args, db_call_kwargs = mock_save_ref.call_args
    table_name = db_call_args[0]
    db_payload = db_call_args[1]

    assert table_name == "credencial_servico_externo"
    assert "service_account_json" not in db_payload # Confirma que o dado sensível não está aqui
    assert db_payload["credenciais_cifradas"] == "vizu-prod-secret-id-gcp-12345" # Apenas o Secret ID está aqui

    # NOVO ASSERÇÃO: Garante que o Rollback NÃO foi chamado no sucesso
    mock_delete_secret.assert_not_called()


@pytest.mark.asyncio
async def test_create_bigquery_credential_validation_error():
    """Testa se a validação Pydantic funciona corretamente (falta project_id)."""
    with pytest.raises(ValidationError):
        BigQueryCredentialCreate(
            cliente_vizu_id="vizu-cliente-b",
            nome_conexao="BQ Incompleto",
            tipo_servico="BIGQUERY",
            project_id=None, # Deve falhar, pois é obrigatório
            service_account_json={"key": "value"}
        )

# NOVO TESTE: Falha no Secret Manager
@pytest.mark.asyncio
async def test_create_credential_secret_manager_error(mock_credential_service, bigquery_payload):
    """
    Testa a falha na chamada inicial ao Secret Manager.
    CRÍTICO: Garante que o DB NUNCA é chamado, pois o fluxo falha no início.
    """
    service, mock_store_secret, mock_save_ref, mock_delete_secret = mock_credential_service

    # Setup: Simula a falha do Secret Manager
    mock_store_secret.side_effect = Exception("Erro de Permissão no Secret Manager")

    with pytest.raises(Exception):
        await service.create_credential(bigquery_payload)

    # Asserções Críticas (Segurança do Fluxo):
    mock_store_secret.assert_called_once()
    mock_save_ref.assert_not_called()     # O DB não deve ser tocado
    mock_delete_secret.assert_not_called() # Não há segredo para dar rollback


# NOVO TESTE: Falha no DB e Acionamento do Rollback
@pytest.mark.asyncio
async def test_create_credential_db_error_triggers_rollback(mock_credential_service, bigquery_payload):
    """
    Testa a falha na persistência do DB após o sucesso do Secret Manager.
    CRÍTICO: Garante que o ROLLBACK (delete_secret) é acionado.
    """
    service, mock_store_secret, mock_save_ref, mock_delete_secret = mock_credential_service

    # Setup: Simula o sucesso do SM e a falha do DB
    mock_save_ref.side_effect = Exception("Erro de Conexão com o Banco de Dados")

    with pytest.raises(Exception):
        await service.create_credential(bigquery_payload)

    # Asserções Críticas (Segurança e Rollback):
    mock_store_secret.assert_called_once() # Deve ter tentado salvar o segredo
    mock_save_ref.assert_called_once()     # Deve ter tentado persistir no DB

    # O teste mais importante: O Rollback deve ser chamado com o ID do segredo
    mock_delete_secret.assert_called_once_with(mock_store_secret.return_value)
