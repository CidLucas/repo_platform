# services/data_processing/tests/test_processor.py

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from src.processor import DataProcessor, ProcessingError


# Fixture com as credenciais que o Worker busca (simula o Secret Manager)
@pytest.fixture
def mock_bigquery_creds():
    """Retorna o JSON da Service Account Key que o Worker usaria."""
    return {
        "type": "service_account",
        "project_id": "vizu-test-project",
        "private_key_id": "mock-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----MOCK_KEY-----END PRIVATE KEY-----\n",
        "client_email": "mock-connector@gcp.iam.gserviceaccount.com",
    }

# Fixture principal para o DataProcessor
@pytest.fixture
def mock_data_processor(mocker, mock_bigquery_creds):
    """
    Configura o DataProcessor mockando suas três principais dependências:
    1. DB Connector (para carga)
    2. Secret Manager (para busca)
    3. BigQuery Connector (para extração)
    """

    # Mocks de Infraestrutura (Injetados no __init__)
    mock_db_connector = MagicMock()
    mock_secret_manager = MagicMock()

    # Mock da Busca de Credenciais (Método interno)
    # Mockamos o método interno para controlar o que ele retorna
    mocker.patch.object(
        DataProcessor,
        '_fetch_real_credentials',
        new_callable=AsyncMock
    )
    # Fazemos o mock retornar o JSON de credenciais
    DataProcessor._fetch_real_credentials.return_value = mock_bigquery_creds

    # Mock do Conector BigQuery (Simula a Extração)
    mock_bq_connector_class = mocker.patch(
        'src.processor.BigQueryConnector',
        # mockamos a classe e simulamos o objeto que ela retorna
    )
    mock_bq_instance = MagicMock()

    # Configura o mock de extração para retornar um DataFrame simulado
    mock_bq_instance.execute_query_to_pandas.return_value = pd.DataFrame({
        'order_id': [1, 2],
        'customer_name': ['Cliente A', 'Cliente B'],
        'total_sales': [100.50, 200.00]
    })

    mock_bq_connector_class.return_value = mock_bq_instance

    # Mock da Carga (Método interno)
    mocker.patch.object(
        DataProcessor,
        '_load_data',
        new_callable=AsyncMock
    )

    # Instancia o processor com os mocks de infra
    processor = DataProcessor(
        db_connector=mock_db_connector,
        secret_manager=mock_secret_manager
    )

    return processor, mock_db_connector, mock_secret_manager, mock_bq_instance


@pytest.mark.asyncio
async def test_process_ingestion_success(mock_data_processor):
    """
    Testa o fluxo ELT completo com mocks simulando sucesso em todas as etapas.
    """
    # Desempacota os objetos mockados
    processor, mock_db, mock_sm, mock_bq_instance = mock_data_processor

    client_id = "vizu-cliente-a"
    cred_id = "uuid-cred-123"

    # Executa o Worker
    result = await processor.process_ingestion(client_id, cred_id)

    # 1. ASSERTIVAS DE FLUXO E MOCKS
    assert result is True
    DataProcessor._fetch_real_credentials.assert_called_once_with(cred_id)

    # 2. ASSERTIVAS DE EXTRAÇÃO
    # Verifica se o conector foi chamado com a query correta
    mock_bq_instance.execute_query_to_pandas.assert_called_once()

    # 3. ASSERTIVAS DE CARGA
    # Verifica se a carga foi chamada e se o DataFrame foi transformado
    DataProcessor._load_data.assert_called_once()

    # Verifica a Transformação (aqui garantimos que a lógica de negócio funcionou)
    # A transformação renomeia 'total_sales' para 'valor_venda'
    loaded_df = DataProcessor._load_data.call_args[0][0]
    assert 'valor_venda' in loaded_df.columns
    assert 'total_sales' not in loaded_df.columns
    assert len(loaded_df) == 2


@pytest.mark.asyncio
async def test_process_ingestion_failure_fetch_credentials(mock_data_processor):
    """
    Testa a falha na primeira etapa (busca de credenciais).
    CRÍTICO: Garante que o fluxo não prossegue.
    """
    processor, mock_db, mock_sm, mock_bq_instance = mock_data_processor

    # Setup: Faz o método de busca de credenciais falhar
    DataProcessor._fetch_real_credentials.side_effect = ProcessingError("Credenciais não encontradas no SM")

    result = await processor.process_ingestion("cliente-x", "uuid-falha")

    assert result is False

    # Assertiva Crítica: O Conector NUNCA deve ser inicializado ou chamado
    mock_bq_instance.execute_query_to_pandas.assert_not_called()
    DataProcessor._load_data.assert_not_called()
