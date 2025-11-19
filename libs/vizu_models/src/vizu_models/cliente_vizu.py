import uuid
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import String, Enum as pgEnum
from sqlalchemy.dialects.postgresql import UUID as pgUUID

from .enums import TipoCliente, TierCliente

# Importações de modelos locais com forward references resolvidas
from .cliente_final import ClienteFinal
from .fonte_de_dados import FonteDeDados
from .credencial_servico_externo import CredencialServicoExterno

if TYPE_CHECKING:
    from .configuracao_negocio import ConfiguracaoNegocio, ConfiguracaoNegocioRead



class ClienteVizuBase(SQLModel):
    nome_empresa: str = Field(max_length=255)
    tipo_cliente: TipoCliente = Field(
        sa_column=Column(pgEnum(TipoCliente, name="tipo_cliente_enum", create_type=False))
    )
    tier: TierCliente = Field(
        sa_column=Column(pgEnum(TierCliente, name="tier_cliente_enum", create_type=False))
    )


class ClienteVizu(ClienteVizuBase, table=True):
    __tablename__ = "cliente_vizu"

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True)
    )
    
    api_key: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(255), unique=True, index=True)
    )

    configuracao: Optional["ConfiguracaoNegocio"] = Relationship(
        back_populates="cliente_vizu", 
        sa_relationship_kwargs={"uselist": False}
    )
    
    clientes_finais: List["ClienteFinal"] = Relationship(back_populates="cliente_vizu")
    fontes_de_dados: List["FonteDeDados"] = Relationship(back_populates="cliente_vizu")
    credenciais: List["CredencialServicoExterno"] = Relationship(back_populates="cliente_vizu")


class ClienteVizuCreate(ClienteVizuBase):
    pass


class ClienteVizuRead(ClienteVizuBase):
    id: uuid.UUID
    api_key: str


class ClienteVizuReadWithRelations(ClienteVizuRead):
    configuracao: Optional["ConfiguracaoNegocioRead"] = None


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""
    nome_empresa: Optional[str] = None
    tipo_cliente: Optional[TipoCliente] = None
    tier: Optional[TierCliente] = None

class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""
    nome_empresa: Optional[str] = None
    tipo_cliente: Optional[TipoCliente] = None
    tier: Optional[TierCliente] = None
