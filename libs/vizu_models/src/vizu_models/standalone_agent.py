import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Agent Catalog
# ---------------------------------------------------------------------------


class AgentCatalogBase(SQLModel):
    name: str = Field(description="Display name of the agent type")
    slug: str = Field(description="Unique URL-safe identifier")
    description: str | None = Field(default=None, description="Human-readable description")
    category: str | None = Field(default=None, description="Grouping category (analytics, knowledge, reporting)")
    icon: str | None = Field(default=None, description="Icon name (Lucide)")


class AgentCatalog(AgentCatalogBase, table=True):
    __tablename__ = "agent_catalog"

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    # Maps 1:1 to AgentConfig dataclass fields
    agent_config: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
        description="AgentConfig-compatible JSONB: {name, role, elicitation_strategy, enabled_tools, max_turns, model, metadata}",
    )

    prompt_name: str = Field(description="Langfuse prompt path (e.g. 'standalone/data-analyst')")

    required_context: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="'[]'::jsonb"),
        description="Fields the Config Helper must collect: [{field, type, required, label, prompt_hint}]",
    )

    required_files: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="'{}'::jsonb"),
        description="File requirements: {csv: {min, max, description}, text: {min, max, description}}",
    )

    requires_google: bool = Field(default=False)

    tier_required: str = Field(default="BASIC")

    is_active: bool = Field(default=True)

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()"),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()"),
    )


class AgentCatalogRead(AgentCatalogBase):
    id: uuid.UUID
    agent_config: dict[str, Any]
    prompt_name: str
    required_context: list[dict[str, Any]]
    required_files: dict[str, Any]
    requires_google: bool
    tier_required: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Standalone Agent Session
# ---------------------------------------------------------------------------


class StandaloneAgentSessionBase(SQLModel):
    config_status: str = Field(default="configuring", description="configuring | ready | active | archived")
    google_account_email: str | None = Field(default=None)


class StandaloneAgentSession(StandaloneAgentSessionBase, table=True):
    __tablename__ = "standalone_agent_sessions"

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    client_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=False,
        )
    )

    agent_catalog_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("agent_catalog.id"),
            nullable=False,
        )
    )

    session_id: str = Field(
        sa_column=Column(Text, unique=True, nullable=False),
        description="LangGraph thread_id / Redis checkpointer key",
    )

    collected_context: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="'{}'::jsonb"),
        description="Key-value pairs gathered by config helper",
    )

    uploaded_file_ids: list[uuid.UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(pgUUID(as_uuid=True)), nullable=False, server_default="'{}'::uuid[]"),
        description="References to uploaded_files_metadata.id (CSV files)",
    )

    uploaded_document_ids: list[uuid.UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(pgUUID(as_uuid=True)), nullable=False, server_default="'{}'::uuid[]"),
        description="References to vector_db.documents.id (embedded docs)",
    )

    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True, server_default="'{}'::jsonb"),
    )

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()"),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()"),
    )


class StandaloneAgentSessionCreate(SQLModel):
    client_id: uuid.UUID
    agent_catalog_id: uuid.UUID
    session_id: str
    google_account_email: str | None = None


class StandaloneAgentSessionRead(StandaloneAgentSessionBase):
    id: uuid.UUID
    client_id: uuid.UUID
    agent_catalog_id: uuid.UUID
    session_id: str
    collected_context: dict[str, Any] = {}
    uploaded_file_ids: list[uuid.UUID] = []
    uploaded_document_ids: list[uuid.UUID] = []
    metadata_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


__all__ = [
    "AgentCatalog",
    "AgentCatalogBase",
    "AgentCatalogRead",
    "StandaloneAgentSession",
    "StandaloneAgentSessionBase",
    "StandaloneAgentSessionCreate",
    "StandaloneAgentSessionRead",
]
