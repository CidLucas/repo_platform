from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import text
from datetime import datetime
import uuid

# Define um tipo UUID que funciona em diferentes bancos de dados
from sqlalchemy.types import UUID as pgUUID

class Base(DeclarativeBase):
    """
    Classe base declarativa para todos os modelos ORM.
    """
    pass

class TimestampMixin:
    """
    Mixin para adicionar colunas de timestamp padrão (criado_em, atualizado_em).
    """
    criado_em: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        onupdate=datetime.utcnow
    )