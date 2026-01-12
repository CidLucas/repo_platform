import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    # Importação para type checking apenas, evita import circular em tempo de execução
    from .cliente_vizu import ClienteVizu


# 1. A Classe BASE deve vir PRIMEIRO
class CredencialServicoExternoBase(SQLModel):
    nome_servico: str = Field(
        ...,
        description="Nome do serviço. Ex: 'google_calendar', 'database_cliente_acme'.",
    )


# 2. A Classe da TABELA herda da Base
class CredencialServicoExterno(CredencialServicoExternoBase, table=True):
    __tablename__ = "credencial_servico_externo"

    id: int | None = Field(default=None, primary_key=True)

    # Relacionamentos e Chaves Estrangeiras
    client_id: uuid.UUID = Field(foreign_key="clientes_vizu.id")

    # Relationship usando string para evitar erro de importação circular no runtime
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="credenciais")


# 3. Schemas de Pydantic (Create/Read/Update) vêm depois
class CredencialServicoExternoCreate(CredencialServicoExternoBase):
    client_id: uuid.UUID
    credenciais: dict


class CredencialServicoExternoInDB(CredencialServicoExternoBase):
    id: int
    client_id: uuid.UUID
