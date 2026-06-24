import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Field, Relationship, SQLModel

from blu_models.enums import TipoFonte

if TYPE_CHECKING:
    from blu_models.cliente_blu import ClienteBlu


class FonteDeDados(SQLModel, table=True):
    __tablename__ = "fonte_de_dados"

    id: int | None = Field(default=None, primary_key=True)
    tipo_fonte: TipoFonte
    caminho: str

    # Supabase FK is client_id pointing to clientes_blu.client_id
    client_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_blu.client_id"),
            nullable=False
        )
    )

    cliente_blu: "ClienteBlu" = Relationship(back_populates="fontes_de_dados")
