import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

# --- Importações Modulares e Organizadas ---
# Dependência de Banco de Dados
from vizu_db_connector.database import get_db_session

# Nossos Schemas (Contratos da API)
from clientes_finais_api.schemas.cliente_final_schemas import (
    ClienteFinalCreate,
    ClienteFinalPublic,
)
# Nossa Camada de Serviço (Lógica de Negócio)
from clientes_finais_api.services.cliente_final_service import ClienteFinalService

# Nossas Dependências de API (Autenticação, etc.)
from .dependencies import get_cliente_vizu_id_from_token

# --- Inicialização ---
logger = logging.getLogger(__name__)
api_router = APIRouter(
    tags=["Clientes Finais"],
)

# --- Dependências Específicas do Roteador ---
def get_cliente_final_service(db: Session = Depends(get_db_session)) -> ClienteFinalService:
    """Função de fábrica para injetar a camada de serviço com a sessão do banco."""
    return ClienteFinalService(db_session=db)


# --- Endpoints da API ---
@api_router.post(
    "/",
    response_model=ClienteFinalPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo Cliente Final",
)
def create_cliente_final(
    cliente_in: ClienteFinalCreate,
    service: ClienteFinalService = Depends(get_cliente_final_service),
    cliente_vizu_id: uuid.UUID = Depends(get_cliente_vizu_id_from_token),
):
    """
    Cria um novo cliente final associado a um Cliente Vizu (identificado pelo token).
    """
    logger.info(f"Recebida requisição de {cliente_vizu_id} para criar cliente final.")
    db_cliente = service.create_cliente_final(
        cliente_in=cliente_in, cliente_vizu_id=cliente_vizu_id
    )
    return db_cliente


@api_router.get(
    "/",
    response_model=List[ClienteFinalPublic],
    summary="Lista os Clientes Finais do Cliente Vizu autenticado",
)
def list_clientes_finais(
    service: ClienteFinalService = Depends(get_cliente_final_service),
    cliente_vizu_id: uuid.UUID = Depends(get_cliente_vizu_id_from_token),
):
    """
    Retorna uma lista de clientes finais **pertencentes ao Cliente Vizu**
    identificado pelo token de autenticação.
    """
    logger.info(f"Recebida requisição de {cliente_vizu_id} para listar seus clientes finais.")
    # A listagem agora é filtrada por cliente_vizu_id para garantir a segurança dos dados.
    return service.list_clientes_finais(cliente_vizu_id=cliente_vizu_id)