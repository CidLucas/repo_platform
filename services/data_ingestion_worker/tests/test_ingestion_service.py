from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from data_ingestion_worker.services.ingestion_service import IngestionService


@pytest.mark.asyncio
async def test_ingestion_service_renames_columns_agnostically(mocker):
    # 1. ARRANGE (Configuração)

    # Mock dos conectores
    mock_connector = MagicMock()
    mock_writer = AsyncMock() # DBWriterService.load é async

    # Mock dos dados que viriam do BigQuery
    source_data = {
        "col_a": [1, 2],
        "col_b": ["x", "y"]
    }
    mock_df = pd.DataFrame(source_data)

    # Configura o mock_connector para retornar o DataFrame mockado
    # (Note: o async_generator é um helper para mockar "async for")
    mock_connector.extract.return_value = async_generator([mock_df])

    # Mock do Mapeamento (O PONTO CHAVE!)
    # Simulamos que o módulo de mapping retornou estas regras
    mock_mapping = {"col_a": "destino_a", "col_b": "destino_b"}
    mock_source_cols = ["col_a", "col_b"]

    # Usamos 'patch' para interceptar a chamada ao módulo de mapping
    mocker.patch(
        "data_ingestion_worker.core.schema_mapping.get_schema_mapping",
        return_value=mock_mapping
    )
    mocker.patch(
        "data_ingestion_worker.core.schema_mapping.get_source_columns",
        return_value=mock_source_cols
    )

    # Instancia o serviço com os mocks
    service = IngestionService(connector=mock_connector, writer=mock_writer)

    # 2. ACT (Ação)
    await service.run_job(job_id="test-job-123", client_id="test-client")

    # 3. ASSERT (Verificação)

    # Verificamos se a query foi construída com as colunas do mapping
    mock_connector.extract.assert_called_once_with(
        "SELECT col_a, col_b "
        "FROM `analytics-big-query-242119.dataform.products_invoices` "
        "ORDER BY col_a"
    )

    # Verificamos se o 'writer' recebeu o DataFrame com as colunas RENOMEADAS
    # Esta é a asserção mais importante!
    called_df = mock_writer.load.call_args[0][0] # Pega o primeiro argumento da chamada de 'load'

    assert "destino_a" in called_df.columns
    assert "destino_b" in called_df.columns
    assert "col_a" not in called_df.columns # Garante que a coluna original foi renomeada

# Helper para mockar 'async for'
async def async_generator(data):
    for item in data:
        yield item
