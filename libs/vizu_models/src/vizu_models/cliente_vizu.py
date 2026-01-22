import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, String, Text, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from sqlmodel import Column, Field, Relationship, SQLModel

# Importações de modelos locais com forward references resolvidas
from .cliente_final import ClienteFinal
from .credencial_servico_externo import CredencialServicoExterno
from .fonte_de_dados import FonteDeDados

if TYPE_CHECKING:
    from .configuracao_negocio import ConfiguracaoNegocio, ConfiguracaoNegocioRead


class ClienteVizuBase(SQLModel):
    # Supabase uses plain text for tipo_cliente and tier, not ENUMs
    nome_empresa: str = Field(default="Empresa")
    tipo_cliente: str | None = Field(default="standard")
    tier: str | None = Field(default="free")


class ClienteVizu(ClienteVizuBase, table=True):
    __tablename__ = "clientes_vizu"

    # Primary key - Supabase uses 'client_id' as PK column name
    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column("client_id", pgUUID(as_uuid=True), primary_key=True),
    )

    # --- Configuration fields ---
    horario_funcionamento: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True, server_default="{}")
    )

    prompt_base: str | None = Field(
        default="Você é um assistente útil.",
        sa_column=Column(Text, nullable=True)
    )

    # Supabase uses ARRAY type for enabled_tools, not JSON
    enabled_tools: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(Text), nullable=True, server_default="ARRAY[]::text[]")
    )



    collection_rag: str | None = Field(
        default="default_collection",
        sa_column=Column(Text, nullable=True)
    )

    # Multi-tenant support - external user ID from OAuth provider
    external_user_id: str | None = Field(
        default=None,
        sa_column=Column(Text, unique=True, nullable=True),
        description="External user ID from OAuth provider (e.g., Supabase auth.users.id)"
    )

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()")
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()")
    )

    clientes_finais: list["ClienteFinal"] = Relationship(back_populates="cliente_vizu")
    fontes_de_dados: list["FonteDeDados"] = Relationship(back_populates="cliente_vizu")
    credenciais: list["CredencialServicoExterno"] = Relationship(
        back_populates="cliente_vizu"
    )
    # Legacy/compat relationship to the old ConfiguracaoNegocio table.
    # Kept as a Relationship so SQLAlchemy mappers remain consistent during
    # the migration rollout. This will be unused once the legacy table is
    # removed in a later migration.
    from typing import Optional as _Optional

    configuracao: _Optional["ConfiguracaoNegocio"] = Relationship(
        back_populates="cliente_vizu"
    )

class ClienteVizuCreate(ClienteVizuBase):
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    enabled_tools: list[str] | None = None
    collection_rag: str | None = None
    external_user_id: str | None = None


class ClienteVizuRead(ClienteVizuBase):
    id: uuid.UUID
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    enabled_tools: list[str] | None = None
    collection_rag: str | None = None
    external_user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClienteVizuReadWithRelations(ClienteVizuRead):
    configuracao: Optional["ConfiguracaoNegocioRead"] = None


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""

    nome_empresa: str | None = None
    tipo_cliente: str | None = None
    tier: str | None = None
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    enabled_tools: list[str] | None = None
    collection_rag: str | None = None
