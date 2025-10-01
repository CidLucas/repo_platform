from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import text
from datetime import datetime
import uuid

# Define um tipo UUID que funciona em diferentes bancos de dados
from sqlalchemy.types import UUID as pgUUID
from sqlalchemy import func  # Importar 'func'

class Base(DeclarativeBase):
    """
    Classe base declarativa para todos os modelos ORM.
    """
    pass


class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(
        server_default=func.now()  # Usar a função now() do banco
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()  # Usar a função now() do banco também no update
    )