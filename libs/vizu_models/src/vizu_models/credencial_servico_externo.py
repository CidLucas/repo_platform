import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


class CredencialServicoExternoBase(SQLModel):
    nome_servico: str = Field(
        description="Nome do serviço. Ex: 'google_calendar', 'bigquery'"
    )


class CredencialServicoExterno(CredencialServicoExternoBase, table=True):
    __tablename__ = "credencial_servico_externo"

    id: int | None = Field(default=None, primary_key=True)

    # FK references clientes_vizu.client_id (the actual column name in Supabase)
    client_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=False
        )
    )

    # Supabase schema fields
    tipo_servico: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    status: str | None = Field(
        default="pending",
        sa_column=Column(Text, nullable=True, server_default="'pending'::text")
    )

    credenciais_cifradas: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )

    connection_metadata: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )

    last_sync_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()")
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, server_default="now()")
    )

    cliente_vizu: "ClienteVizu" = Relationship(back_populates="credenciais")


class CredencialServicoExternoCreate(CredencialServicoExternoBase):
    client_id: uuid.UUID
    tipo_servico: str | None = None
    credenciais_cifradas: str | None = None
    connection_metadata: dict | None = None


class CredencialServicoExternoInDB(CredencialServicoExternoBase):
    id: int
    client_id: uuid.UUID
    tipo_servico: str | None
    status: str | None
    created_at: datetime | None
    updated_at: datetime | None
