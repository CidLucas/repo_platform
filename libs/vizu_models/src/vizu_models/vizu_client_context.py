import uuid
from sqlmodel import SQLModel
from .cliente_vizu import TierCliente

class VizuClientContext(SQLModel):
    """
    Data model for holding the context of a Vizu client during a request.
    This is a Pydantic-style model and not a database table.
    """
    cliente_id: uuid.UUID
    nome_empresa: str
    tier: TierCliente
    # Adicione outros campos que eram usados no contexto
