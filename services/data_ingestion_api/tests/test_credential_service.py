# services/data_ingestion_api/tests/test_credential_service.py

from unittest.mock import AsyncMock

import pytest
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
        client_id="550e8400-e29b-41d4-a716-446655440000",
        nome_conexao="BQ Dados Financeiros",
        tipo_servico="BIGQUERY",
        project_id="projeto-cliente-a-prod",
        service_account_json=service_account_data
    )


@pytest.fixture
def mock_credential_service(mocker):
    """Cria uma instância do CredentialService com mocks para Vault e DB."""

    # 1. Mock do Supabase insert (creates credential record)
    mock_insert = mocker.patch(
        'data_ingestion_api.services.supabase_client.insert',
        new_callable=AsyncMock
    )
    mock_insert.return_value = {
        "id": 123,
        "client_id": "550e8400-e29b-41d4-a716-446655440000",
        "nome_servico": "BQ Dados Financeiros",
        "tipo_servico": "BIGQUERY",
        "status": "pending",
    }

    # 2. Mock do Supabase RPC (stores in vault)
    mock_rpc = mocker.patch(
        'data_ingestion_api.services.supabase_client.rpc',
        new_callable=AsyncMock
    )
    mock_rpc.return_value = "vault-key-uuid-12345"

    # 3. Mock do Supabase update (sets vault_key_id)
    mock_update = mocker.patch(
        'data_ingestion_api.services.supabase_client.update',
        new_callable=AsyncMock
    )
    mock_update.return_value = [{"id": 123, "vault_key_id": "vault-key-uuid-12345"}]

    service = CredentialService()

    return service, mock_insert, mock_rpc, mock_update


@pytest.mark.asyncio
async def test_create_bigquery_credential_success(mock_credential_service, bigquery_payload):
    """
    Testa o fluxo completo de criação de credenciais BigQuery.
    CRÍTICO: Garante que credentials são armazenadas no vault, não no DB.
    """
    service, mock_insert, mock_rpc, mock_update = mock_credential_service

    response = await service.create_credential(bigquery_payload)

    # A) Verifica que o registro foi criado sem credentials
    mock_insert.assert_called_once()
    insert_args = mock_insert.call_args[0]
    table_name = insert_args[0]
    db_payload = insert_args[1]

    assert table_name == "credencial_servico_externo"
    assert "service_account_json" not in db_payload
    assert "credenciais_cifradas" not in db_payload
    assert db_payload["status"] == "pending"

    # B) Verifica que o vault RPC foi chamado
    mock_rpc.assert_called_once()
    rpc_args = mock_rpc.call_args[0]
    assert rpc_args[0] == "store_credential_in_vault"
    rpc_params = rpc_args[1]
    assert "p_credentials" in rpc_params
    assert "service_account_json" in rpc_params["p_credentials"]

    # C) Verifica que o vault_key_id foi salvo
    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[1] == {"vault_key_id": "vault-key-uuid-12345"}

    # D) Verifica a resposta
    assert response.id_credencial == "123"
    assert response.secret_manager_id == "vault:vault-key-uuid-12345"
    assert response.status == "PENDENTE_VALIDACAO"


@pytest.mark.asyncio
async def test_create_bigquery_credential_validation_error():
    """Testa se a validação Pydantic funciona corretamente (falta project_id)."""
    with pytest.raises(ValidationError):
        BigQueryCredentialCreate(
            client_id="550e8400-e29b-41d4-a716-446655440000",
            nome_conexao="BQ Incompleto",
            tipo_servico="BIGQUERY",
            project_id=None,
            service_account_json={"key": "value"}
        )


@pytest.mark.asyncio
async def test_create_credential_vault_error(mock_credential_service, bigquery_payload):
    """
    Testa a falha na chamada ao Vault RPC.
    """
    service, mock_insert, mock_rpc, mock_update = mock_credential_service

    mock_rpc.side_effect = Exception("Vault RPC failed")

    with pytest.raises(Exception):
        await service.create_credential(bigquery_payload)

    mock_insert.assert_called_once()
    mock_rpc.assert_called_once()
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_create_credential_db_insert_error(mock_credential_service, bigquery_payload):
    """
    Testa a falha na inserção inicial do registro.
    """
    service, mock_insert, mock_rpc, mock_update = mock_credential_service

    mock_insert.side_effect = Exception("Database connection error")

    with pytest.raises(Exception):
        await service.create_credential(bigquery_payload)

    mock_insert.assert_called_once()
    mock_rpc.assert_not_called()
    mock_update.assert_not_called()
