# libs/vizu_shared_models/src/vizu_shared_models/ingestion/schema_config.py

from pydantic import BaseModel, Field
from typing import Dict, List
from enum import Enum
from .vizu_schema import VizuCanonicalColumn

# --- ADICIONADO ---
# Enum para tipos de formatação que precisamos lidar
class ColumnFormat(str, Enum):
    """Formatos de dados que o nosso sistema deve suportar."""
    STRING = "STRING"
    STRING_DATE_YMD = "YYYY-MM-DD"
    UNIX_TIMESTAMP_SECONDS = "UNIX_SECONDS"
    UNIX_TIMESTAMP_MILLIS = "UNIX_MILLIS"
    # Adicione outros formatos conforme necessário (ex: DECIMAL_COMMA)

# --- ADICIONADO ---
class ColumnConfig(BaseModel):
    """Configuração detalhada por coluna a ser extraída."""
    
    # Nome da coluna no schema CANÔNICO Vizu
    vizu_name: VizuCanonicalColumn = Field(..., description="Nome da coluna no schema canônico Vizu.")
    
    # Nome da coluna no schema DO CLIENTE (para o SELECT SQL)
    client_name: str = Field(..., description="Nome real da coluna na tabela do cliente (Ex: 'created_at').")
    
    # O formato do dado na tabela do cliente (para a transformação)
    client_format: ColumnFormat = Field(..., description="O formato do dado de origem.")

    # Flag para normalização de texto
    apply_text_normalization: bool = Field(
        default=False, 
        description="Se True, aplica a normalização padrão Vizu (lowercase, sem acentos, trim)."
    )

# --- ATUALIZADO ---
class ClientSchemaMapping(BaseModel):
    """
    Modelo de Mapeamento para um Cliente/Job de Ingestão específico.
    Usado para traduzir o schema do cliente para o nosso schema canônico.
    """
    
    # 1. Identificação da Fonte
    client_id: str = Field(..., description="ID exclusivo do Cliente.")
    source_table_name: str = Field(..., description="Nome exato da tabela de origem no BigQuery.")
    
    # 2. O Mapeamento (ATUALIZADO)
    # Agora mapeia o nome Canônico Vizu para a Configuração Detalhada
    column_mappings: Dict[VizuCanonicalColumn, ColumnConfig] = Field(
        ...,
        description="Mapeamento de configurações para o schema canônico Vizu."
    )
    
    # 3. Configuração de Extração (Resolve o seu erro E2E!)
    chunk_key_column_name: str = Field(
        ...,
        description="O nome REAL da coluna do cliente que deve ser usada para ordenação/chunking (Ex: 'data_de_faturamento')."
    )
    
    # 4. Colunas Selecionadas
    select_columns: List[str] = Field(
        ...,
        description="Lista de nomes de colunas (NO CLIENTE) que o Worker deve incluir na cláusula SELECT.",
        min_length=1
    )