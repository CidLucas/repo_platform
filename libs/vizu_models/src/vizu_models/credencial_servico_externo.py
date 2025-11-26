import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    # Importação para type checking apenas, evita import circular em tempo de execução
    from .cliente_vizu import ClienteVizu

# 1. A Classe BASE deve vir PRIMEIRO
class CredencialServicoExternoBase(SQLModel):
    nome_servico: str = Field(..., description="Nome do serviço. Ex: 'google_calendar', 'database_cliente_acme'.")

# 2. A Classe da TABELA herda da Base
class CredencialServicoExterno(CredencialServicoExternoBase, table=True):
    __tablename__ = "credencial_servico_externo"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relacionamentos e Chaves Estrangeiras
    cliente_vizu_id: uuid.UUID = Field(foreign_key="cliente_vizu.id")

    # Relationship usando string para evitar erro de importação circular no runtime
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="credenciais")

# 3. Schemas de Pydantic (Create/Read/Update) vêm depois
class CredencialServicoExternoCreate(CredencialServicoExternoBase):
    cliente_vizu_id: uuid.UUID
    credenciais: dict

class CredencialServicoExternoInDB(CredencialServicoExternoBase):
    id: int
    cliente_vizu_id: uuid.UUID