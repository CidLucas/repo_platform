# services/clients_api/src/clients_api/api/endpoints/configuracoes.py (VERSÃO COMPLETA E FINAL)
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Importa os modelos Pydantic e SQLAlchemy relevantes
from vizu_models import (
    ConfiguracaoNegocioCreate,
    ConfiguracaoNegocioUpdate,
    ConfiguracaoNegocio,
    ClienteVizu,
)
from ...services.config_service import config_service
from ..dependencies import get_db_session

router = APIRouter()


# --- Endpoint de Criação (POST) ---
@router.post("", response_model=ConfiguracaoNegocio, status_code=201)
def create_configuracao(
    *,
    db_session: Session = Depends(get_db_session),
    config_in: ConfiguracaoNegocioCreate,
):
    """
    Cria uma nova configuração de negócio para um Cliente Vizu.
    """
    # Instead of creating a separate ConfiguracaoNegocio row, persist the fields
    # directly on the ClienteVizu row (merged model).
    cliente = (
        db_session.query(ClienteVizu)
        .filter(ClienteVizu.id == config_in.cliente_vizu_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # Prevent creating duplicate legacy rows: if a separate config exists, return conflict
    config_existente = config_service.get_by_cliente(
        db_session=db_session, cliente_vizu_id=config_in.cliente_vizu_id
    )
    if config_existente:
        # We'll treat this as an update request for safety
        raise HTTPException(
            status_code=400,
            detail="Uma configuração já existe para este cliente. Use PUT para atualizar.",
        )

    # Map incoming payload into cliente fields
    cliente.prompt_base = getattr(config_in, "prompt_base", cliente.prompt_base)
    cliente.horario_funcionamento = getattr(
        config_in, "horario_funcionamento", cliente.horario_funcionamento
    )
    cliente.ferramenta_rag_habilitada = getattr(
        config_in, "ferramenta_rag_habilitada", cliente.ferramenta_rag_habilitada
    )
    cliente.ferramenta_sql_habilitada = getattr(
        config_in, "ferramenta_sql_habilitada", cliente.ferramenta_sql_habilitada
    )
    cliente.ferramenta_agendamento_habilitada = getattr(
        config_in,
        "ferramenta_agendamento_habilitada",
        cliente.ferramenta_agendamento_habilitada,
    )
    cliente.collection_rag = getattr(
        config_in, "collection_rag", cliente.collection_rag
    )

    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)

    # Return a representation compatible with the old ConfiguracaoNegocio shape
    return {
        "id": None,
        "cliente_vizu_id": str(cliente.id),
        "prompt_base": cliente.prompt_base,
        "horario_funcionamento": cliente.horario_funcionamento,
        "ferramenta_rag_habilitada": cliente.ferramenta_rag_habilitada,
        "ferramenta_sql_habilitada": cliente.ferramenta_sql_habilitada,
        "ferramenta_agendamento_habilitada": cliente.ferramenta_agendamento_habilitada,
        "collection_rag": cliente.collection_rag,
    }


# --- Endpoint de Leitura (GET) ---
@router.get("/by-client/{cliente_id}", response_model=ConfiguracaoNegocio)
def read_configuracao_by_cliente(
    *, db_session: Session = Depends(get_db_session), cliente_id: uuid.UUID
):
    """
    Retorna a configuração de negócio de um Cliente Vizu específico pelo ID do cliente.
    """
    # Read directly from cliente_vizu merged fields
    cliente = db_session.query(ClienteVizu).filter(ClienteVizu.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    return {
        "id": None,
        "cliente_vizu_id": str(cliente.id),
        "prompt_base": cliente.prompt_base,
        "horario_funcionamento": cliente.horario_funcionamento,
        "ferramenta_rag_habilitada": cliente.ferramenta_rag_habilitada,
        "ferramenta_sql_habilitada": cliente.ferramenta_sql_habilitada,
        "ferramenta_agendamento_habilitada": cliente.ferramenta_agendamento_habilitada,
        "collection_rag": cliente.collection_rag,
    }


# --- Endpoint de Atualização (PUT) ---
@router.put("/{config_id}", response_model=ConfiguracaoNegocio)
def update_configuracao(
    *,
    db_session: Session = Depends(get_db_session),
    config_id: int,
    config_in: ConfiguracaoNegocioUpdate,
):
    """
    Atualiza uma configuração de negócio existente pelo seu ID.
    """
    # For merged model we identify the cliente from the legacy config row
    config_db = config_service.get(db=db_session, id=config_id)
    if not config_db:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")

    cliente = (
        db_session.query(ClienteVizu)
        .filter(ClienteVizu.id == config_db.cliente_vizu_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente associado não encontrado.")

    # Apply updates
    for field in [
        "prompt_base",
        "horario_funcionamento",
        "ferramenta_rag_habilitada",
        "ferramenta_sql_habilitada",
        "ferramenta_agendamento_habilitada",
        "collection_rag",
    ]:
        if hasattr(config_in, field) and getattr(config_in, field) is not None:
            setattr(cliente, field, getattr(config_in, field))

    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)

    return {
        "id": config_db.id,
        "cliente_vizu_id": str(cliente.id),
        "prompt_base": cliente.prompt_base,
        "horario_funcionamento": cliente.horario_funcionamento,
        "ferramenta_rag_habilitada": cliente.ferramenta_rag_habilitada,
        "ferramenta_sql_habilitada": cliente.ferramenta_sql_habilitada,
        "ferramenta_agendamento_habilitada": cliente.ferramenta_agendamento_habilitada,
        "collection_rag": cliente.collection_rag,
    }


# --- Endpoint de Deleção (DELETE) ---
@router.delete("/{config_id}", status_code=204)
def delete_configuracao(
    *, db_session: Session = Depends(get_db_session), config_id: int
):
    """
    Deleta uma configuração de negócio pelo seu ID.
    """
    config_db = config_service.get(db=db_session, id=config_id)
    if not config_db:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")

    # Clear merged fields on cliente_vizu instead of removing cliente
    cliente = (
        db_session.query(ClienteVizu)
        .filter(ClienteVizu.id == config_db.cliente_vizu_id)
        .first()
    )
    if cliente:
        cliente.prompt_base = None
        cliente.horario_funcionamento = None
        cliente.ferramenta_rag_habilitada = False
        cliente.ferramenta_sql_habilitada = False
        cliente.ferramenta_agendamento_habilitada = False
        cliente.collection_rag = None
        db_session.add(cliente)
        db_session.commit()

    # Optionally remove legacy config row to keep data single-sourced
    try:
        config_service.remove(db=db_session, id=config_id)
    except Exception:
        # If removal fails keep going; the important part is clearing cliente_vizu
        pass

    return
