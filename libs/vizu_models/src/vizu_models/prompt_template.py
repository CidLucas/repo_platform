"""
Prompt Template Models

Tabela para armazenar prompts versionados que podem ser:
- Globais (client_id = NULL) - templates padrão do sistema
- Por cliente (client_id != NULL) - customizações específicas

Integração com MCP: @mcp.prompt() pode buscar templates desta tabela.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


class PromptTemplateBase(SQLModel):
    """Base fields for prompt templates."""

    name: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Identificador único do prompt (ex: 'atendente/system', 'rag/query')",
    )

    version: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False),
        description="Versão do prompt (incrementada a cada update)",
    )

    content: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Conteúdo do prompt com placeholders {{variable}}",
    )

    description: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Descrição do propósito do prompt",
    )

    variables: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Schema das variáveis esperadas (JSON Schema)",
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default="true"),
        description="Se este prompt está ativo para uso",
    )

    tags: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Tags para categorização (ex: ['system', 'v2', 'experimental'])",
    )


class PromptTemplate(PromptTemplateBase, table=True):
    """
    Tabela de prompts versionados.

    Uso:
    - client_id = NULL: Prompt global/default
    - client_id != NULL: Override específico para o cliente

    A combinação (name, version, client_id) deve ser única.
    """

    __tablename__ = "prompt_template"
    __table_args__ = (
        UniqueConstraint(
            "name", "version", "client_id", name="uq_prompt_name_version_client"
        ),
    )

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    client_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=True,
            index=True,
        ),
        description="NULL para prompts globais, UUID para prompts específicos do cliente",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    created_by: str | None = Field(
        default=None,
        sa_column=Column(String(100)),
        description="Quem criou o prompt (para auditoria)",
    )

    # Relationship
    cliente_vizu: Optional["ClienteVizu"] = Relationship()


class PromptTemplateCreate(PromptTemplateBase):
    """Schema para criar um novo prompt."""

    client_id: uuid.UUID | None = None


class PromptTemplateRead(PromptTemplateBase):
    """Schema para leitura de prompt."""

    id: uuid.UUID
    client_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None


class PromptTemplateUpdate(SQLModel):
    """Schema para atualizar um prompt (cria nova versão)."""

    content: str | None = None
    description: str | None = None
    variables: dict | None = None
    is_active: bool | None = None
    tags: list[str] | None = None
