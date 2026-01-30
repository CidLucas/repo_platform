import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, Text, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID as pgUUID, JSONB
from sqlmodel import Column, Field, Relationship, SQLModel

# Importações de modelos locais com forward references resolvidas
from .cliente_final import ClienteFinal
from .credencial_servico_externo import CredencialServicoExterno
from .fonte_de_dados import FonteDeDados

if TYPE_CHECKING:
    from .configuracao_negocio import ConfiguracaoNegocio, ConfiguracaoNegocioRead


class ClienteVizuBase(SQLModel):
    """
    Base fields for ClienteVizu.

    Context 2.0: All context sections are embedded as JSONB columns.
    """
    # Core Identity
    nome_empresa: str = Field(default="Empresa")
    cpf_cnpj: str | None = Field(default=None, description="CPF ou CNPJ do cliente")
    tier: str | None = Field(default="BASIC", description="BASIC, SME, ENTERPRISE")

    # Legacy field - kept for backward compatibility
    tipo_cliente: str | None = Field(default="standard")


class ClienteVizu(ClienteVizuBase, table=True):
    """
    Main client table with embedded context sections (Context 2.0).

    Structure:
    - Core identity: client_id, nome_empresa, cpf_cnpj, tier
    - Auth: external_user_id
    - Context sections: JSONB columns for each section type
    - Legacy: prompt_base, enabled_tools (deprecated, use available_tools section)
    """
    __tablename__ = "clientes_vizu"

    # ===== PRIMARY KEY =====
    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column("client_id", pgUUID(as_uuid=True), primary_key=True),
    )

    # ===== AUTH =====
    external_user_id: str | None = Field(
        default=None,
        sa_column=Column(Text, unique=True, nullable=True),
        description="External user ID from OAuth provider (e.g., Supabase auth.users.id)"
    )

    # ===== IDENTIFICATION =====
    cpf_cnpj: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="CPF ou CNPJ do cliente"
    )

    # ===== CONTEXT SECTIONS (Context 2.0) =====
    # Core Identity (quarterly updates)
    company_profile: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Company identity: mission, vision, values, archetype"
    )

    brand_voice: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Communication style: tone, phrases to use/avoid"
    )

    # Business (monthly updates)
    product_catalog: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Products and services offered"
    )

    target_audience: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="ICP, buyer personas, pain points"
    )

    market_context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Competitors, differentiators, regulations"
    )

    # Operations (weekly updates)
    current_moment: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Current priorities, challenges, wins, metrics"
    )

    team_structure: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Key contacts, escalation paths, business hours"
    )

    policies: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Rules, guardrails, approval workflows"
    )

    # Technical (on-change updates)
    data_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Available data tables, formats, key fields"
    )

    available_tools: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Tool permissions, limits, default prompts"
    )

    # Custom extension
    client_custom: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Client-specific custom context"
    )

    # ===== LEGACY FIELDS (deprecated - use context sections) =====
    horario_funcionamento: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True, server_default="{}"),
        description="DEPRECATED: Use team_structure.business_hours"
    )

    prompt_base: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="DEPRECATED: Use available_tools.default_system_prompt"
    )

    enabled_tools: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(Text), nullable=True, server_default="ARRAY[]::text[]"),
        description="DEPRECATED: Use available_tools.enabled_tool_names"
    )

    collection_rag: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="RAG collection name"
    )

    # ===== TIMESTAMPS =====
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()")
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()")
    )

    # ===== RELATIONSHIPS =====
    clientes_finais: list["ClienteFinal"] = Relationship(back_populates="cliente_vizu")
    fontes_de_dados: list["FonteDeDados"] = Relationship(back_populates="cliente_vizu")
    credenciais: list["CredencialServicoExterno"] = Relationship(
        back_populates="cliente_vizu"
    )

    # Legacy relationship - kept for migration compatibility
    from typing import Optional as _Optional
    configuracao: _Optional["ConfiguracaoNegocio"] = Relationship(
        back_populates="cliente_vizu"
    )

    # ===== HELPER METHODS =====
    def get_enabled_tools_list(self) -> list[str]:
        """
        Get list of enabled tools (Context 2.0 compatible).

        Prefers available_tools section, falls back to legacy enabled_tools.
        """
        if self.available_tools and self.available_tools.get("enabled_tool_names"):
            return self.available_tools["enabled_tool_names"]
        return list(self.enabled_tools or [])

    def get_default_prompt(self) -> str | None:
        """
        Get default system prompt (Context 2.0 compatible).

        Prefers available_tools section, falls back to legacy prompt_base.
        """
        if self.available_tools and self.available_tools.get("default_system_prompt"):
            return self.available_tools["default_system_prompt"]
        return self.prompt_base

    def get_business_hours(self) -> dict | None:
        """
        Get business hours (Context 2.0 compatible).

        Prefers team_structure section, falls back to legacy horario_funcionamento.
        """
        if self.team_structure and self.team_structure.get("business_hours"):
            return {"horario": self.team_structure["business_hours"]}
        return self.horario_funcionamento


# ===== API SCHEMAS =====

class ClienteVizuCreate(ClienteVizuBase):
    """Schema for creating a new client."""
    external_user_id: str | None = None

    # Context sections
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    product_catalog: dict[str, Any] | None = None
    target_audience: dict[str, Any] | None = None
    market_context: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None
    client_custom: dict[str, Any] | None = None

    # Legacy (optional)
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    enabled_tools: list[str] | None = None
    collection_rag: str | None = None


class ClienteVizuRead(ClienteVizuBase):
    """Schema for reading a client."""
    id: uuid.UUID
    external_user_id: str | None = None

    # Context sections
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    product_catalog: dict[str, Any] | None = None
    target_audience: dict[str, Any] | None = None
    market_context: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None
    client_custom: dict[str, Any] | None = None

    # Legacy
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    enabled_tools: list[str] | None = None
    collection_rag: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClienteVizuReadWithRelations(ClienteVizuRead):
    """Schema for reading a client with related data."""
    configuracao: Optional["ConfiguracaoNegocioRead"] = None


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client. All fields are optional."""
    nome_empresa: str | None = None
    cpf_cnpj: str | None = None
    tier: str | None = None
    tipo_cliente: str | None = None

    # Context sections
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    product_catalog: dict[str, Any] | None = None
    target_audience: dict[str, Any] | None = None
    market_context: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None
    client_custom: dict[str, Any] | None = None

    # Legacy
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    enabled_tools: list[str] | None = None
    collection_rag: str | None = None
