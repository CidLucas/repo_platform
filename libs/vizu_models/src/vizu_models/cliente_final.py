import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.types import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

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

    cliente_vizu_id: uuid.UUID = Field(foreign_key="cliente_vizu.id")
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="clientes_finais")


class ClienteFinalCreate(ClienteFinalBase):
    cliente_vizu_id: uuid.UUID


class ClienteFinalRead(ClienteFinalBase):
    id: int
    cliente_vizu_id: uuid.UUID


class ClienteFinalUpdate(SQLModel):
    nome: str | None = None
    metadados: dict[str, Any] | None = None
