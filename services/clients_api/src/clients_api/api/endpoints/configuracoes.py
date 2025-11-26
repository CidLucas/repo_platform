# services/clients_api/src/clients_api/api/endpoints/configuracoes.py (VERSÃO COMPLETA E FINAL)
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Importa os modelos Pydantic e SQLAlchemy relevantes
from vizu_models import ConfiguracaoNegocioCreate, ConfiguracaoNegocioUpdate, ConfiguracaoNegocio
from ...services.config_service import config_service
from ..dependencies import get_db_session

router = APIRouter()

# --- Endpoint de Criação (POST) ---
@router.post("", response_model=ConfiguracaoNegocio, status_code=201)
def create_configuracao(
    *,
    db_session: Session = Depends(get_db_session),
    config_in: ConfiguracaoNegocioCreate
):
    """
    Cria uma nova configuração de negócio para um Cliente Vizu.
    """
    # Lógica de negócio: impede a criação de uma configuração duplicada para o mesmo cliente.
    config_existente = config_service.get_by_cliente(db_session=db_session, cliente_vizu_id=config_in.cliente_vizu_id)
    if config_existente:
        raise HTTPException(
            status_code=400,
            detail="Uma configuração já existe para este cliente. Use o endpoint PUT para atualizá-la."
        )

    # Usa o método 'create' da nossa BaseCRUD (herdado pelo service)
    return config_service.create(db=db_session, obj_in=config_in)

# --- Endpoint de Leitura (GET) ---
@router.get("/by-client/{cliente_id}", response_model=ConfiguracaoNegocio)
def read_configuracao_by_cliente(
    *,
    db_session: Session = Depends(get_db_session),
    cliente_id: uuid.UUID
):
    """
    Retorna a configuração de negócio de um Cliente Vizu específico pelo ID do cliente.
    """
    config = config_service.get_by_cliente(db_session=db_session, cliente_vizu_id=cliente_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada para este cliente.")
    return config

# --- Endpoint de Atualização (PUT) ---
@router.put("/{config_id}", response_model=ConfiguracaoNegocio)
def update_configuracao(
    *,
    db_session: Session = Depends(get_db_session),
    config_id: int,
    config_in: ConfiguracaoNegocioUpdate
):
    """
    Atualiza uma configuração de negócio existente pelo seu ID.
    """
    config_db = config_service.get(db=db_session, id=config_id)
    if not config_db:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")

    # Usa o método 'update' da nossa BaseCRUD
    config_atualizada = config_service.update(db=db_session, db_obj=config_db, obj_in=config_in)
    return config_atualizada

# --- Endpoint de Deleção (DELETE) ---
@router.delete("/{config_id}", status_code=204)
def delete_configuracao(
    *,
    db_session: Session = Depends(get_db_session),
    config_id: int
):
    """
    Deleta uma configuração de negócio pelo seu ID.
    """
    config_db = config_service.get(db=db_session, id=config_id)
    if not config_db:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")

    # Usa o método 'remove' da nossa BaseCRUD
    config_service.remove(db=db_session, id=config_id)

    # Retorna uma resposta vazia com status 204 No Content
    return