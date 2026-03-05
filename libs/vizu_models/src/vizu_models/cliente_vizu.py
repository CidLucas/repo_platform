import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, Field, Relationship, SQLModel

# Importações de modelos locais com forward references resolvidas
from .cliente_final import ClienteFinal
from .credencial_servico_externo import CredencialServicoExterno
from .fonte_de_dados import FonteDeDados


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
    Main client table with Context 2.0 sections for prompt injection.

    Context sections (JSONB):
    - company_profile: Company identity, mission, values
    - brand_voice: Communication style, tone, phrases
    - current_moment: Weekly priorities, challenges, metrics
    - team_structure: Contacts, business hours, escalation
    - policies: Business rules, guardrails, forbidden topics
    - data_schema: Available data tables for SQL agent
    - available_tools: enabled_tool_names, default_system_prompt

    Tool configuration:
    - tier: BASIC, SME, ENTERPRISE (tool access level)
    - enabled_tools: Tool whitelist array
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
    # These JSONB columns store client-specific data for prompt injection

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
        description="Tool permissions: enabled_tool_names list and default_system_prompt"
    )

    # ===== TOOL CONFIGURATION =====
    enabled_tools: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(Text), nullable=True, server_default="ARRAY[]::text[]"),
        description="DEPRECATED: Use available_tools.enabled_tool_names"
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
        Get default system prompt from Context 2.0 available_tools section.
        """
        if self.available_tools and self.available_tools.get("default_system_prompt"):
            return self.available_tools["default_system_prompt"]
        return None

    def get_business_hours(self) -> str | None:
        """
        Get business hours from Context 2.0 team_structure section.
        """
        if self.team_structure and self.team_structure.get("business_hours"):
            return self.team_structure["business_hours"]
        return None

    def get_rag_collection(self) -> str | None:
        """
        Get RAG collection name from Context 2.0 available_tools section.
        """
        if self.available_tools and self.available_tools.get("rag_collection"):
            return self.available_tools["rag_collection"]
        return None


# ===== API SCHEMAS =====

class ClienteVizuCreate(ClienteVizuBase):
    """Schema for creating a new client."""
    external_user_id: str | None = None

    # Context 2.0 sections
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None  # Contains business_hours
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None  # Contains rag_collection, default_system_prompt

    # Tool configuration
    enabled_tools: list[str] | None = None


class ClienteVizuRead(ClienteVizuBase):
    """Schema for reading a client."""
    id: uuid.UUID
    external_user_id: str | None = None

    # Context 2.0 sections
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None

    # Tool configuration
    enabled_tools: list[str] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClienteVizuReadWithRelations(ClienteVizuRead):
    """Schema for reading a client with related data."""
    pass


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client. All fields are optional."""
    nome_empresa: str | None = None
    cpf_cnpj: str | None = None
    tier: str | None = None
    tipo_cliente: str | None = None

    # Context 2.0 sections
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None

    # Tool configuration
    enabled_tools: list[str] | None = None
