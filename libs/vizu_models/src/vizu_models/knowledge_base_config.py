"""
Knowledge Base Configuration Models

Tabela para armazenar configurações de knowledge bases por cliente.
Permite que cada cliente tenha múltiplas bases de conhecimento com metadados.

Integração com MCP: @mcp.resource("knowledge://...") busca desta tabela.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


class KnowledgeBaseConfigBase(SQLModel):
    """Base fields for knowledge base configuration."""

    name: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Nome identificador da base de conhecimento (ex: 'servicos', 'faq', 'produtos')",
    )

    description: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Descrição do conteúdo da base",
    )

    collection_name: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Nome da collection no Qdrant",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        sa_column=Column(String(100), nullable=False),
        description="Modelo de embedding usado",
    )

    chunk_size: int = Field(
        default=512,
        sa_column=Column(Integer, nullable=False),
        description="Tamanho do chunk para splitting",
    )

    chunk_overlap: int = Field(
        default=50,
        sa_column=Column(Integer, nullable=False),
        description="Overlap entre chunks",
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default="true"),
        description="Se esta base está ativa para busca",
    )

    metadata_schema: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Schema esperado dos metadados dos documentos",
    )

    search_config: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Configurações de busca (top_k, score_threshold, etc.)",
    )


class KnowledgeBaseConfig(KnowledgeBaseConfigBase, table=True):
    """
    Tabela de configurações de knowledge bases.

    Cada cliente pode ter múltiplas bases de conhecimento.
    """

    __tablename__ = "knowledge_base_config"

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    client_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=False,
            index=True,
        )
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    # Stats (atualizado por jobs de sync)
    document_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
        description="Número de documentos na base",
    )

    last_sync_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime),
        description="Última sincronização com Qdrant",
    )

    # Relationship
    cliente_vizu: Optional["ClienteVizu"] = Relationship()


class KnowledgeBaseConfigCreate(KnowledgeBaseConfigBase):
    """Schema para criar uma nova base de conhecimento."""

    client_id: uuid.UUID


class KnowledgeBaseConfigRead(KnowledgeBaseConfigBase):
    """Schema para leitura de base de conhecimento."""

    id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    document_count: int
    last_sync_at: datetime | None = None


class KnowledgeBaseConfigUpdate(SQLModel):
    """Schema para atualizar uma base de conhecimento."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    search_config: dict | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
