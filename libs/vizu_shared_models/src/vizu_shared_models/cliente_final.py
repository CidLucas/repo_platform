import uuid
from typing import Dict, Any
from pydantic import Field

from .core import BaseSchema

class ClienteFinalBase(BaseSchema):
    id_externo: str = Field(..., description="O identificador principal do cliente final. Ex: número de telefone.")
    nome: str | None = Field(None, max_length=255)
    metadados: Dict[str, Any] | None = Field(None, description='Campo flexível para dados não estruturados. Ex: {"preferencias": ["sem picles"]}')


class ClienteFinalCreate(ClienteFinalBase):
    cliente_vizu_id: uuid.UUID


class ClienteFinalInDB(ClienteFinalBase):
    id: int
    cliente_vizu_id: uuid.UUID