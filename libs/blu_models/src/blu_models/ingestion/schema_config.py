# libs/blu_models/src/blu_models/ingestion/schema_config.py
from __future__ import annotations

from enum import Enum

from sqlmodel import Field, SQLModel

from .blu_schema import BluCanonicalColumn


class ColumnFormat(Enum):
    """Formatos de dados que o nosso sistema deve suportar."""

    STRING = "STRING"
    STRING_DATE_YMD = "YYYY-MM-DD"
    UNIX_TIMESTAMP_SECONDS = "UNIX_SECONDS"
    UNIX_TIMESTAMP_MILLIS = "UNIX_MILLIS"


class ColumnConfig(SQLModel):
    """Configuração detalhada por coluna a ser extraída."""

    blu_name: BluCanonicalColumn = Field(
        ..., description="Nome da coluna no schema canônico Blu."
    )
    client_name: str = Field(
        ..., description="Nome real da coluna na tabela do cliente (Ex: 'created_at')."
    )
    client_format: ColumnFormat = Field(..., description="O formato do dado de origem.")
    apply_text_normalization: bool = Field(
        default=False,
        description="Se True, aplica a normalização padrão Blu (lowercase, sem acentos, trim).",
    )


class ClientSchemaMapping(SQLModel):
    """
    Modelo de Mapeamento para um Cliente/Job de Ingestão específico.
    Usado para traduzir o schema do cliente para o nosso schema canônico.
    """

    client_id: str = Field(..., description="ID exclusivo do Cliente.")
    source_table_name: str = Field(
        ..., description="Nome exato da tabela de origem no BigQuery."
    )
    column_mappings: dict[BluCanonicalColumn, ColumnConfig] = Field(
        ..., description="Mapeamento de configurações para o schema canônico Blu."
    )
    chunk_key_column_name: str = Field(
        ...,
        description="O nome REAL da coluna do cliente que deve ser usada para ordenação/chunking (Ex: 'data_de_faturamento').",
    )
    select_columns: list[str] = Field(
        ...,
        description="Lista de nomes de colunas (NO CLIENTE) que o Worker deve incluir na cláusula SELECT.",
        min_items=1,
    )
