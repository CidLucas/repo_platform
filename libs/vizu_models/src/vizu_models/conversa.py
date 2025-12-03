import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy import Text, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as pgUUID


class Remetente(str, Enum):
    USER = "user"
    AI = "ai"


class ConversaBase(SQLModel):
    # Timestamp de início com timezone
    timestamp_inicio: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Conversa(ConversaBase, table=True):
    """Tabela de conversas persistida no Postgres."""

    __tablename__ = "conversa"

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    # Session id (string) para mapear sessões temporárias (ex: session_id usado pelo agente)
    session_id: Optional[str] = Field(default=None, index=True)

    # Referência ao cliente Vizu (tenant) - obrigatório para RLS
    cliente_vizu_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("cliente_vizu.id", ondelete="CASCADE"),
            index=True,
        ),
    )

    # Referência ao cliente final (opcional)
    cliente_final_id: Optional[int] = Field(
        default=None, foreign_key="cliente_final.id"
    )

    # Relationship to messages (optional convenience, not required)
    mensagens: list["Mensagem"] = Relationship(back_populates="conversa")


class ConversaCreate(ConversaBase):
    cliente_vizu_id: Optional[uuid.UUID] = None
    cliente_final_id: Optional[int] = None


class ConversaInDB(ConversaBase):
    id: uuid.UUID
    cliente_vizu_id: Optional[uuid.UUID]
    cliente_final_id: Optional[int]


class MensagemBase(SQLModel):
    # Use SQLAlchemy Enum with values_callable to use enum values (lowercase) not names (uppercase)
    remetente: Remetente = Field(
        sa_column=Column(
            SAEnum(
                Remetente,
                values_callable=lambda x: [e.value for e in x],
                name="remetente_enum",
                create_type=False,
            )
        )
    )
    # Use TEXT in DB to avoid length limits on messages
    conteudo: str = Field(sa_column=Column(Text))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )


class Mensagem(MensagemBase, table=True):
    """Tabela de mensagens ligadas a uma conversa."""

    __tablename__ = "mensagem"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversa_id: uuid.UUID = Field(
        sa_column=Column(pgUUID(as_uuid=True), ForeignKey("conversa.id"))
    )

    # Relationship back to conversation
    conversa: Optional[Conversa] = Relationship(back_populates="mensagens")


class MensagemCreate(MensagemBase):
    conversa_id: uuid.UUID


class MensagemInDB(MensagemBase):
    id: int
    conversa_id: uuid.UUID
