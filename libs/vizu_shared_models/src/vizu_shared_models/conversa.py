import uuid
from datetime import datetime, timezone  # 1. Importar o 'timezone'
from enum import Enum
from pydantic import Field

from .core import BaseSchema

class Remetente(str, Enum):
    USER = "user"
    AI = "ai"

class ConversaBase(BaseSchema):
    # 2. Usar a forma moderna e timezone-aware para o valor padrão
    timestamp_inicio: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class ConversaCreate(ConversaBase):
    cliente_final_id: int

class ConversaInDB(ConversaBase):
    id: uuid.UUID
    cliente_final_id: int

class MensagemBase(BaseSchema):
    remetente: Remetente
    conteudo: str

class MensagemCreate(MensagemBase):
    conversa_id: uuid.UUID

class MensagemInDB(MensagemBase):
    id: int
    conversa_id: uuid.UUID