# tests/unit/test_data_transformers.py
import pytest
import pandas as pd
from datetime import datetime
from vizu_shared_utils.data_transformers import transform_data
from vizu_models.ingestion.schema_config import ColumnConfig, ColumnFormat
from vizu_models.ingestion.vizu_schema import VizuCanonicalColumn

def test_transform_unix_timestamp_seconds_to_datetime():
    # SETUP: Dados Brutos do Cliente
    data = {
        'id_transacao': [1, 2],
        'created_at': [1609459200, 1640995200] # Unix Timestamp (Segundos)
    }
    df_raw = pd.DataFrame(data)

    # SETUP: Configuração de Mapeamento
    mappings = {
        VizuCanonicalColumn.INVOICE_DATE: ColumnConfig(
            vizu_name=VizuCanonicalColumn.INVOICE_DATE,
            client_name='created_at',
            client_format=ColumnFormat.UNIX_TIMESTAMP_SECONDS
        )
    }

    # ACT
    df_transformed = transform_data(df_raw.copy(), mappings)

    # ASSERT (Testabilidade)
    # 1. A coluna deve ser renomeada para o nosso padrão canônico
    assert VizuCanonicalColumn.INVOICE_DATE.value in df_transformed.columns
    assert 'created_at' not in df_transformed.columns

    # 2. O formato deve ser convertido para datetime
    assert pd.api.types.is_datetime64_any_dtype(df_transformed[VizuCanonicalColumn.INVOICE_DATE.value])

    # 3. Os valores devem ser corretos (1/Jan/2021 e 1/Jan/2022)
    expected_dates = [datetime(2021, 1, 1, 0, 0), datetime(2022, 1, 1, 0, 0)]
    assert all(df_transformed[VizuCanonicalColumn.INVOICE_DATE.value] == expected_dates)

def test_transform_data_applies_text_normalization():
    # SETUP: Dados Brutos do Cliente
    data = {'Nome_Produto_Cliente': ["Produto Ação", "  PRODUTO B  ", "Maçã"]}
    df_raw = pd.DataFrame(data)

    # SETUP: Configuração
    mappings = {
        VizuCanonicalColumn.PRODUCT_NAME: ColumnConfig(
            vizu_name=VizuCanonicalColumn.PRODUCT_NAME,
            client_name='Nome_Produto_Cliente',
            client_format=ColumnFormat.STRING,
            apply_text_normalization=True # Flag ativada
        )
    }

    # ACT
    df_transformed = transform_data(df_raw.copy(), mappings)

    # ASSERT
    expected_values = ["produto acao", "produto b", "maca"]
    column_name = VizuCanonicalColumn.PRODUCT_NAME.value

    assert column_name in df_transformed.columns
    assert all(df_transformed[column_name] == expected_values)