# libs/vizu_models/src/vizu_models/client_context_section.py
"""
Client context section models (Context 2.0).

Database model and schemas for modular client context storage.
Each client can have multiple sections, each storing a different
type of context (company profile, brand voice, current moment, etc.).
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, SQLModel
from sqlmodel import Field as SQLField

from .enums import ContextSection


class ClientContextSectionBase(SQLModel):
    """Base model for context sections."""

    section_type: ContextSection = SQLField(
        description="Type of context section (e.g., company_profile, brand_voice)"
    )
    content: dict[str, Any] = SQLField(
        default_factory=dict,
        description="Section content as JSONB - structure depends on section_type",
    )
    is_active: bool = SQLField(
        default=True,
        description="Whether this section is currently active",
    )
    version: int = SQLField(
        default=1,
        description="Version number, auto-incremented on updates",
    )


class ClientContextSection(ClientContextSectionBase, table=True):
    """
    Database model for client context sections.

    Stores modular context data per client. Each section type can have
    only one active record per client (enforced by unique constraint).

    Table: client_context_sections
    """

    __tablename__ = "client_context_sections"

    id: uuid.UUID | None = SQLField(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    client_id: uuid.UUID = SQLField(
        sa_column=Column(
            pgUUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        description="FK to clientes_vizu.client_id",
    )

    # Store section_type as TEXT in DB (enum validation in Python)
    section_type: ContextSection = SQLField(
        sa_column=Column(Text, nullable=False),
    )

    content: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )

    is_active: bool = SQLField(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
    )

    version: int = SQLField(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default="1"),
    )

    last_updated_at: datetime | None = SQLField(
        default=None,
        sa_column=Column(
            "last_updated_at",
            nullable=True,
        ),
    )

    updated_by: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Who last updated this section",
    )

    created_at: datetime | None = SQLField(
        default=None,
        sa_column=Column(
            "created_at",
            nullable=True,
        ),
    )


# =============================================================================
# API Schemas
# =============================================================================


class ClientContextSectionCreate(BaseModel):
    """Schema for creating a context section."""

    model_config = ConfigDict(use_enum_values=True)

    client_id: uuid.UUID
    section_type: ContextSection
    content: dict[str, Any]
    updated_by: str | None = None


class ClientContextSectionUpdate(BaseModel):
    """Schema for updating a context section."""

    content: dict[str, Any]
    updated_by: str | None = None


class ClientContextSectionRead(BaseModel):
    """Schema for reading a context section."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    client_id: uuid.UUID
    section_type: ContextSection
    content: dict[str, Any]
    is_active: bool
    version: int
    last_updated_at: datetime | None
    updated_by: str | None
    created_at: datetime | None


class ClientContextSectionSummary(BaseModel):
    """Lightweight summary of a section (for listing)."""

    model_config = ConfigDict(use_enum_values=True)

    section_type: ContextSection
    version: int
    last_updated_at: datetime | None
    updated_by: str | None


# =============================================================================
# Bulk Operations
# =============================================================================


class BulkSectionUpsert(BaseModel):
    """Schema for upserting multiple sections at once."""

    sections: dict[ContextSection, dict[str, Any]] = Field(
        description="Map of section_type to content"
    )
    updated_by: str | None = None


class BulkSectionResponse(BaseModel):
    """Response for bulk section operations."""

    client_id: uuid.UUID
    updated_sections: list[ContextSection]
    failed_sections: list[tuple[ContextSection, str]] = Field(
        default_factory=list,
        description="List of (section_type, error_message) for failures",
    )
