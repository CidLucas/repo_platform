
from __future__ import annotations

from sqlmodel import SQLModel

from .cliente_blu import TierCliente, TipoCliente


class ClienteBluUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""

    nome_empresa: str | None = None
    tipo_cliente: TipoCliente | None = None
    tier: TierCliente | None = None
