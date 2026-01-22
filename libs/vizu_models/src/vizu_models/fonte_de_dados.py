import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Field, Relationship, SQLModel

from .enums import TipoFonte

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


class FonteDeDados(SQLModel, table=True):
    __tablename__ = "fonte_de_dados"

    id: int | None = Field(default=None, primary_key=True)
    tipo_fonte: TipoFonte
    caminho: str

    # Supabase FK is cliente_vizu_id pointing to clientes_vizu.client_id
    cliente_vizu_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=False
        )
    )

    cliente_vizu: "ClienteVizu" = Relationship(back_populates="fontes_de_dados")
