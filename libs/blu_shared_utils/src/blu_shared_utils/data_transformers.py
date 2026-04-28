# libs/blu_shared_utils/data_transformers.py


import pandas as pd

from blu_models.ingestion.schema_config import ColumnConfig, ColumnFormat
from blu_models.ingestion.blu_schema import BluCanonicalColumn
from blu_shared_utils.text_utils import normalize_text  # Importa a função modular


def transform_data(df: pd.DataFrame, mappings: dict[BluCanonicalColumn, ColumnConfig]) -> pd.DataFrame:
    """
    Normaliza os dados brutos de um cliente para o Schema Canônico Blu.
    """
    for blu_name, config in mappings.items():
        client_name = config.client_name

        # 1. Renomear para o Schema Canônico Blu
        if client_name in df.columns:
            df.rename(columns={client_name: blu_name.value}, inplace=True)
        else:
            # Tratamento de erro ou log (coluna esperada não encontrada)
            continue

        # 2. Aplicar a Transformação de Formato
        if config.client_format == ColumnFormat.UNIX_TIMESTAMP_SECONDS:
            # Exemplo de tratamento para Unix Timestamp em segundos
            df[blu_name.value] = pd.to_datetime(df[blu_name.value], unit='s')
        elif config.client_format == ColumnFormat.UNIX_TIMESTAMP_MILLIS:
            # Exemplo de tratamento para Unix Timestamp em milissegundos
            df[blu_name.value] = pd.to_datetime(df[blu_name.value], unit='ms')

        # NOVA LÓGICA DE LIMPEZA DE TEXTO (Agnóstica)
        if config.apply_text_normalization:
            # Aplica a função de normalização na coluna inteira (vetorizado pelo Pandas)
            df[blu_name.value] = df[blu_name.value].apply(normalize_text)

    return df
