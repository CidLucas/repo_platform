import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from vizu_models import ClienteVizu, ConfiguracaoNegocio

def get_cliente_vizu_by_api_key(db: Session, api_key: str):
    """Busca cliente pela API Key (Usada na autenticação inicial)"""
    statement = select(ClienteVizu).where(ClienteVizu.api_key == api_key)
    return db.execute(statement).scalars().first()

def get_cliente_vizu_by_id(db: Session, cliente_id: uuid.UUID):
    """Busca cliente pelo ID trazendo a configuração junto (Eager Load)."""
    statement = select(ClienteVizu).where(ClienteVizu.id == cliente_id)
    return db.execute(statement).scalars().first()

def get_configuracao_negocio(db: Session, cliente_id: uuid.UUID):
    """Busca as configurações de negócio de um cliente"""
    # Transitional helper: query legacy configuracao_negocio by cliente_vizu_id
    statement = select(ConfiguracaoNegocio).where(ConfiguracaoNegocio.cliente_vizu_id == cliente_id)
    return db.execute(statement).scalars().first()