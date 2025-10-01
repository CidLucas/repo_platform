import uuid
from sqlalchemy import ForeignKey, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as pgUUID

from .base import Base

class ConfiguracaoNegocio(Base):
    __tablename__ = "configuracao_negocio"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_vizu_id: Mapped[uuid.UUID] = mapped_column(
        pgUUID(as_uuid=True), ForeignKey("cliente_vizu.id"), unique=True
    )

    prompt_base: Mapped[str | None] = mapped_column(Text)
    horario_funcionamento: Mapped[dict | None] = mapped_column(JSON)
    ferramenta_rag_habilitada: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relacionamento
    cliente_vizu = relationship("ClienteVizu", back_populates="configuracao")