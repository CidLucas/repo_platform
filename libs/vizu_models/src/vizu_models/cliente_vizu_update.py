
from sqlmodel import SQLModel

from .cliente_vizu import TierCliente, TipoCliente


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""

    nome_empresa: str | None = None
    tipo_cliente: TipoCliente | None = None
    tier: TierCliente | None = None
