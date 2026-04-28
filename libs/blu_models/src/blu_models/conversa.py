import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, Field, Relationship, SQLModel


class Remetente(Enum):
    USER = "user"
    AI = "ai"


class ConversaBase(SQLModel):
    # Timestamp de início com timezone
    timestamp_inicio: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class Conversa(ConversaBase, table=True):
    """Tabela de conversas persistida no Postgres."""

    __tablename__ = "conversa"

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    # Session id (string) para mapear sessões temporárias
    session_id: str | None = Field(default=None, index=True)

    # Referência ao cliente final (opcional)
    # Note: Supabase schema does NOT have client_id FK, only cliente_final_id
    cliente_final_id: int | None = Field(
        default=None, foreign_key="cliente_final.id"
    )

    # Relationship to messages (optional convenience, not required)
    mensagens: list["Mensagem"] = Relationship(back_populates="conversa")


class ConversaCreate(ConversaBase):
    cliente_final_id: int | None = None


class ConversaInDB(ConversaBase):
    id: uuid.UUID
    cliente_final_id: int | None


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
        default_factory=lambda: datetime.now(UTC), index=True
    )


class Mensagem(MensagemBase, table=True):
    """Tabela de mensagens ligadas a uma conversa."""

    __tablename__ = "mensagem"

    id: int | None = Field(default=None, primary_key=True)
    conversa_id: uuid.UUID = Field(
        sa_column=Column(pgUUID(as_uuid=True), ForeignKey("conversa.id"))
    )

    # Relationship back to conversation
    conversa: Conversa | None = Relationship(back_populates="mensagens")


class MensagemCreate(MensagemBase):
    conversa_id: uuid.UUID


class MensagemInDB(MensagemBase):
    id: int
    conversa_id: uuid.UUID
