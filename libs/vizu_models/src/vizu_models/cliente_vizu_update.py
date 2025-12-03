from typing import Optional
from sqlmodel import SQLModel
from .cliente_vizu import TipoCliente, TierCliente


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""

    nome_empresa: Optional[str] = None
    tipo_cliente: Optional[TipoCliente] = None
    tier: Optional[TierCliente] = None
