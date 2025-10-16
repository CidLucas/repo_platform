# services/clients_api/src/clients_api/api/endpoints/clientes.py (VERSÃO COMPLETA)
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vizu_shared_models.cliente_vizu import ClienteVizuCreate, ClienteVizuUpdate, ClienteVizuInDB
from ..dependencies import get_db_session, get_client_service
from ...services.client_service import ClienteVizuService

# Este é o router específico para os endpoints de clientes
router = APIRouter()

@router.post("", response_model=ClienteVizuInDB, status_code=201)
def create_cliente_vizu(
    *,
    db_session: Session = Depends(get_db_session),
    cliente_in: ClienteVizuCreate,
    client_service: ClienteVizuService = Depends(get_client_service)
):
    return client_service.create_cliente_vizu(db_session=db_session, cliente_in=cliente_in)

@router.get("", response_model=List[ClienteVizuInDB])
def read_clientes_vizu(
    db_session: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
    client_service: ClienteVizuService = Depends(get_client_service)
):
    return client_service.get_multi(db=db_session, skip=skip, limit=limit)

@router.get("/{cliente_id}", response_model=ClienteVizuInDB)
def read_cliente_vizu(
    *,
    db_session: Session = Depends(get_db_session),
    cliente_id: uuid.UUID,
    client_service: ClienteVizuService = Depends(get_client_service)
):
    cliente = client_service.get(db=db_session, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

@router.put("/{cliente_id}", response_model=ClienteVizuInDB)
def update_cliente_vizu(
    *,
    db_session: Session = Depends(get_db_session),
    cliente_id: uuid.UUID,
    cliente_in: ClienteVizuUpdate,
    client_service: ClienteVizuService = Depends(get_client_service)
):
    cliente_db = client_service.get(db=db_session, id=cliente_id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client_service.update(db=db_session, db_obj=cliente_db, obj_in=cliente_in)

@router.delete("/{cliente_id}", status_code=204)
def delete_cliente_vizu(
    *,
    db_session: Session = Depends(get_db_session),
    cliente_id: uuid.UUID,
    client_service: ClienteVizuService = Depends(get_client_service)
):
    cliente_db = client_service.get(db=db_session, id=cliente_id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    client_service.remove(db=db_session, id=cliente_id)
    return