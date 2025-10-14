import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from vizu_db_connector.database import get_db_session
from vizu_shared_models.cliente_vizu import ClienteVizuCreate, ClienteVizuBase
from ..services.client_service import ClientService

router = APIRouter()
logger = logging.getLogger(__name__)

def get_client_service(db: Session = Depends(get_db_session)) -> ClientService:
    return ClientService(db)

@router.post("/clientes", response_model=ClienteVizuBase, status_code=201, tags=["Clientes"])
def create_cliente_vizu(
    cliente_in: ClienteVizuCreate,
    service: ClientService = Depends(get_client_service)
):
    """
    Cria um novo Cliente Vizu.
    """
    logger.info(f"Tentativa de criação de cliente para a empresa: {cliente_in.nome_empresa}")

    cliente_existente = service.get_by_email(email=cliente_in.email_contato)
    if cliente_existente:
        logger.warning(f"Cliente com email {cliente_in.email_contato} já existe.")
        raise HTTPException(
            status_code=400,
            detail="Um cliente com este email já está cadastrado.",
        )

    cliente = service.create(cliente_create=cliente_in)
    logger.info(f"Cliente Vizu criado com sucesso com o ID: {cliente.id}")
    return cliente