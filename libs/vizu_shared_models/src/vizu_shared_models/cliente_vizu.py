import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from .core import BaseSchema

class TipoCliente(str, Enum):
    EXTERNO = "externo"
    INTERNO = "interno"

class TierCliente(str, Enum):
    SME = "sme"
    ENTERPRISE = "enterprise"


class ClienteVizuBase(BaseSchema):
    nome_empresa: str = Field(..., max_length=255)
    tipo_cliente: TipoCliente = Field(..., description="Diferencia clientes ('externo') de projetos ('interno').")
    tier: TierCliente = Field(..., description="Nível do cliente para controle de recursos.")


class ClienteVizuCreate(ClienteVizuBase):
    pass


class ClienteVizuInDB(ClienteVizuBase):
    id: uuid.UUID
    api_key: str
    criado_em: datetime