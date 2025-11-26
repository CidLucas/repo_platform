# services/clients_api/src/clients_api/api/endpoints/clientes.py (VERSÃO REATORADA)
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

# Modelos compartilhados que definem o contrato da API
from vizu_models import (
    ClienteVizuCreate,
    ClienteVizuRead,
    ClienteVizuUpdate,
)

# Dependências que injetam a sessão do DB e a lógica de serviço
from ..dependencies import get_db_session, get_client_service
from ...services.client_service import ClienteVizuService

# --- Router para os Endpoints de Clientes ---
router = APIRouter()

@router.post("/", response_model=ClienteVizuRead, status_code=201,
             summary="Cria um novo Cliente Vizu",
             description="Cria um novo cliente e retorna seus dados públicos, omitindo a api_key.")
def create_cliente(
    *,
    cliente_in: ClienteVizuCreate,
    db: Session = Depends(get_db_session),
    client_service: ClienteVizuService = Depends(get_client_service)
):
    """
    Cria um novo cliente a partir dos dados fornecidos.

    - **Segurança**: Retorna o modelo `ClienteVizuRead`, que não expõe a `api_key`.
    """
    # A lógica de negócio fica encapsulada no serviço
    return client_service.create_cliente_vizu(db_session=db, cliente_in=cliente_in)

@router.get("/", response_model=List[ClienteVizuRead],
            summary="Lista todos os Clientes Vizu",
            description="Retorna uma lista de clientes com dados públicos.")
def read_clientes(
    *,
    db: Session = Depends(get_db_session),
    client_service: ClienteVizuService = Depends(get_client_service),
    skip: int = 0,
    limit: int = 100
):
    """
    Retorna uma lista paginada de clientes.
    """
    return client_service.get_multi(db=db, skip=skip, limit=limit)

@router.get("/{cliente_id}", response_model=ClienteVizuRead,
            summary="Busca um Cliente Vizu por ID",
            description="Retorna os dados públicos de um cliente específico.")
def read_cliente_by_id(
    *,
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    client_service: ClienteVizuService = Depends(get_client_service)
):
    """
    Busca um cliente pelo seu ID.

    - Retorna `404 Not Found` se o cliente não existir.
    """
    cliente_db = client_service.get(db=db, id=cliente_id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente_db

@router.put("/{cliente_id}", response_model=ClienteVizuRead,
            summary="Atualiza um Cliente Vizu",
            description="Atualiza os dados de um cliente e retorna a versão atualizada e pública.")
def update_cliente(
    *,
    cliente_id: uuid.UUID,
    cliente_in: ClienteVizuUpdate,
    db: Session = Depends(get_db_session),
    client_service: ClienteVizuService = Depends(get_client_service)
):
    """
    Atualiza um cliente existente.

    - **Segurança**: Retorna o modelo `ClienteVizuRead` para não expor a `api_key` após a atualização.
    """
    cliente_db = client_service.get(db=db, id=cliente_id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return client_service.update(db=db, db_obj=cliente_db, obj_in=cliente_in)

@router.delete("/{cliente_id}", status_code=204,
               summary="Deleta um Cliente Vizu",
               description="Remove um cliente do banco de dados.")
def delete_cliente(
    *,
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    client_service: ClienteVizuService = Depends(get_client_service)
):
    """
    Deleta um cliente pelo seu ID.

    - Retorna `204 No Content` em caso de sucesso.
    - Retorna `404 Not Found` se o cliente não existir para deleção.
    """
    cliente_db = client_service.get(db=db, id=cliente_id)
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    client_service.remove(db=db, id=cliente_id)
    # Retorna uma resposta vazia com o status code 204
    return Response(status_code=204)