import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as pgUUID

from .base import Base

class CredencialServicoExterno(Base):
    __tablename__ = "credencial_servico_externo"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_vizu_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("cliente_vizu.id"))

    nome_servico: Mapped[str] = mapped_column(String, comment="Nome do serviço. Ex: 'google_calendar', 'database_cliente_acme'.")
    credenciais_cifradas: Mapped[str] = mapped_column(Text, comment="Valor criptografado das credenciais.")

    # Relacionamento
    cliente_vizu = relationship("ClienteVizu", back_populates="credenciais")