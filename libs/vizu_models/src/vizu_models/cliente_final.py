import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


class ClienteFinalBase(SQLModel):
    id_externo: str = Field(
        ...,
        description="O identificador principal do cliente final. Ex: número de telefone.",
        index=True,
    )
    nome: str | None = Field(None, max_length=255)
    metadados: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Campo flexível para dados não estruturados.",
    )


class ClienteFinal(ClienteFinalBase, table=True):
    __tablename__ = "cliente_final"

    id: int | None = Field(default=None, primary_key=True)

    # Supabase FK is cliente_vizu_id pointing to clientes_vizu.client_id
    cliente_vizu_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=False
        )
    )
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="clientes_finais")


class ClienteFinalCreate(ClienteFinalBase):
    cliente_vizu_id: uuid.UUID


class ClienteFinalRead(ClienteFinalBase):
    id: int
    cliente_vizu_id: uuid.UUID


class ClienteFinalUpdate(SQLModel):
    nome: str | None = None
    metadados: dict[str, Any] | None = None
