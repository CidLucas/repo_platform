import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu

class CredencialServicoExterno(SQLModel, table=True):
    __tablename__ = "credencial_servico_externo" # Supondo o nome da tabela

    id: Optional[int] = Field(default=None, primary_key=True)
    # Adicione outros campos conforme necessário

    cliente_vizu_id: uuid.UUID = Field(foreign_key="cliente_vizu.id")
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="credenciais")
