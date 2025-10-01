import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, Enum as pgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as pgUUID

from .base import Base, TimestampMixin

# Reutilizamos o Enum do nosso pacote de modelos Pydantic
from vizu_shared_models.conversa import Remetente

class Conversa(Base):
    __tablename__ = "conversa"

    id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_final_id: Mapped[int] = mapped_column(Integer, ForeignKey("cliente_final.id"))
    timestamp_inicio: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente_final = relationship("ClienteFinal", back_populates="conversas")
    mensagens = relationship("Mensagem", back_populates="conversa", cascade="all, delete-orphan")

class Mensagem(Base, TimestampMixin):
    __tablename__ = "mensagem"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversa_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("conversa.id"))

    remetente: Mapped[Remetente] = mapped_column(pgEnum(Remetente, name="remetente_enum"))
    conteudo: Mapped[str] = mapped_column(Text)

    # Relacionamento
    conversa = relationship("Conversa", back_populates="mensagens")