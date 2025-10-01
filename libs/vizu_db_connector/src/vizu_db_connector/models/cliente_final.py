import uuid
from sqlalchemy import String, JSON, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as pgUUID

from .base import Base

class ClienteFinal(Base):
    __tablename__ = "cliente_final"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_vizu_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("cliente_vizu.id"))

    id_externo: Mapped[str] = mapped_column(String, index=True, doc="O identificador principal do cliente final. Ex: número de telefone.")
    nome: Mapped[str | None] = mapped_column(String(255))
    metadados: Mapped[dict | None] = mapped_column(JSON, doc='Campo flexível para dados não estruturados.')

    # Relacionamentos
    cliente_vizu = relationship("ClienteVizu", back_populates="clientes_finais")
    conversas = relationship("Conversa", back_populates="cliente_final")