import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from .enums import TipoFonte

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu

class FonteDeDados(SQLModel, table=True):
    __tablename__ = "fonte_de_dados" # Supondo o nome da tabela

    id: Optional[int] = Field(default=None, primary_key=True)
    tipo_fonte: TipoFonte
    caminho: str
    # Adicione outros campos conforme necessário

    cliente_vizu_id: uuid.UUID = Field(foreign_key="cliente_vizu.id")
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="fontes_de_dados")
