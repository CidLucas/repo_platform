import uuid
from datetime import datetime, timezone  # 1. Importar o 'timezone'
from enum import Enum
from sqlmodel import Field, SQLModel


class Remetente(str, Enum):
    USER = "user"
    AI = "ai"

class ConversaBase(SQLModel):
    # 2. Usar a forma moderna e timezone-aware para o valor padrão
    timestamp_inicio: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class ConversaCreate(ConversaBase):
    cliente_final_id: int

class ConversaInDB(ConversaBase):
    id: uuid.UUID
    cliente_final_id: int

class MensagemBase(SQLModel):
    remetente: Remetente
    conteudo: str

class MensagemCreate(MensagemBase):
    conversa_id: uuid.UUID

class MensagemInDB(MensagemBase):
    id: int
    conversa_id: uuid.UUID