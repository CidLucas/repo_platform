# libs/vizu_shared_utils/data_transformers.py

import pandas as pd
from datetime import datetime
from typing import Dict
from vizu_shared_models.ingestion.schema_config import ColumnFormat, ColumnConfig
from vizu_shared_models.ingestion.vizu_schema import VizuCanonicalColumn
from vizu_shared_utils.text_utils import normalize_text # Importa a função modular

def transform_data(df: pd.DataFrame, mappings: Dict[VizuCanonicalColumn, ColumnConfig]) -> pd.DataFrame:
    """
    Normaliza os dados brutos de um cliente para o Schema Canônico Vizu.
    """
    for vizu_name, config in mappings.items():
        client_name = config.client_name
        
        # 1. Renomear para o Schema Canônico Vizu
        if client_name in df.columns:
            df.rename(columns={client_name: vizu_name.value}, inplace=True)
        else:
            # Tratamento de erro ou log (coluna esperada não encontrada)
            continue
            
        # 2. Aplicar a Transformação de Formato
        if config.client_format == ColumnFormat.UNIX_TIMESTAMP_SECONDS:
            # Exemplo de tratamento para Unix Timestamp em segundos
            df[vizu_name.value] = pd.to_datetime(df[vizu_name.value], unit='s')
        elif config.client_format == ColumnFormat.UNIX_TIMESTAMP_MILLIS:
            # Exemplo de tratamento para Unix Timestamp em milissegundos
            df[vizu_name.value] = pd.to_datetime(df[vizu_name.value], unit='ms')

        # NOVA LÓGICA DE LIMPEZA DE TEXTO (Agnóstica)
        if config.apply_text_normalization:
            # Aplica a função de normalização na coluna inteira (vetorizado pelo Pandas)
            df[vizu_name.value] = df[vizu_name.value].apply(normalize_text)
        
    return df