import uuid
from sqlalchemy import String, Enum as pgEnum, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as pgUUID
from enum import Enum

from .base import Base, TimestampMixin

# NOTA: Idealmente, estes Enums deveriam estar em 'vizu-shared-models'
# para serem compartilhados com a camada de validação Pydantic.
class TipoFonte(str, Enum):
    PDF = "pdf"
    URL = "url"
    TXT = "txt"
    JSON = "json"

class StatusIndexacao(str, Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    FALHA = "falha"

class FonteDeDados(Base, TimestampMixin):
    __tablename__ = "fonte_de_dados"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_vizu_id: Mapped[uuid.UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("cliente_vizu.id"))

    tipo_fonte: Mapped[TipoFonte] = mapped_column(pgEnum(TipoFonte, name="tipo_fonte_enum"))
    caminho: Mapped[str] = mapped_column(String, comment="URL, caminho para o arquivo no GCS, etc.")
    status_indexacao: Mapped[StatusIndexacao] = mapped_column(pgEnum(StatusIndexacao, name="status_indexacao_enum"), default=StatusIndexacao.PENDENTE)
    hash_conteudo: Mapped[str | None] = mapped_column(String(64), comment="SHA-256 do conteúdo para detectar mudanças.")
    metadados_indexacao: Mapped[dict | None] = mapped_column(JSON, comment="Metadados do processo de indexação, como número de chunks, erros, etc.")

    # Relacionamento
    cliente_vizu = relationship("ClienteVizu", back_populates="fontes_de_dados")