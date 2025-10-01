import uuid
from sqlalchemy import String, Enum as pgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as pgUUID

from .base import Base, TimestampMixin
from typing import List # Adicionar este import

# Reutilizamos os Enums definidos em vizu-shared-models para consistência,
# mas poderíamos redefini-los aqui se quisessemos desacoplar totalmente.
# Para este exemplo, vamos assumir que a lib de models está instalada no ambiente.
from vizu_shared_models.cliente_vizu import TipoCliente, TierCliente


class ClienteVizu(Base, TimestampMixin):
    __tablename__ = "cliente_vizu"

    id: Mapped[uuid.UUID] = mapped_column(
        pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome_empresa: Mapped[str] = mapped_column(String(255))
    api_key: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    tipo_cliente: Mapped[TipoCliente] = mapped_column(pgEnum(TipoCliente, name="tipo_cliente_enum"))
    tier: Mapped[TierCliente] = mapped_column(pgEnum(TierCliente, name="tier_cliente_enum"))

    # Relacionamentos
    configuracao = relationship("ConfiguracaoNegocio", back_populates="cliente_vizu", uselist=False)
    clientes_finais = relationship("ClienteFinal", back_populates="cliente_vizu")

    configuracao = relationship("ConfiguracaoNegocio", back_populates="cliente_vizu", uselist=False)
    clientes_finais = relationship("ClienteFinal", back_populates="cliente_vizu")

    # Adicionar estas duas linhas:
    fontes_de_dados: Mapped[List["FonteDeDados"]] = relationship("FonteDeDados", back_populates="cliente_vizu")
    credenciais: Mapped[List["CredencialServicoExterno"]] = relationship("CredencialServicoExterno", back_populates="cliente_vizu")
