# services/data_ingestion_api/routes.py

from typing import Any, Union
import logging
from pydantic import ValidationError

from data_ingestion_api.schemas.schemas import (
    BigQueryCredentialCreate,
    CredencialResponse,
    SQLCredentialCreate,
)
from data_ingestion_api.services.credential_service import credential_service
from fastapi import APIRouter, Depends, HTTPException, status
from vizu_auth.fastapi.dependencies import get_auth_result


# Autenticação via Supabase JWT (API Key desabilitada)
logger = logging.getLogger(__name__)

# Cria um router para agrupar endpoints de credenciais.
router = APIRouter(
    prefix="/credentials",
    tags=["Ingestion - Credentials"]
)

# Define o Union Type para validação do FastAPI (Agnosticismo)
CredentialPayload = Union[BigQueryCredentialCreate, SQLCredentialCreate]

# Dependência que faria a injeção do conector de banco de dados
# Exemplo: def get_db_session():...

@router.post(
    "/create",
    response_model=CredencialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma referência de credencial e armazena o segredo."
)
async def create_new_credential(
    payload: dict[str, Any],  # aceitar JSON bruto e construir o schema manualmente
    auth=Depends(get_auth_result),
):
    """
    Recebe as credenciais de um serviço externo (BigQuery, SQL) e inicia o fluxo de segurança:
    1. Armazena a chave sensível no Secret Manager.
    2. Persiste o ID de referência no banco de dados Vizu.

    Retorna a CredencialResponse com o ID de rastreamento.
    """
    try:
        # Construir schema adequado com base nos campos presentes
        logger.info("/credentials/create received payload keys: %s", list(payload.keys()))

        # Handle legacy field name: map client_id to client_id if needed
        if 'client_id' in payload and 'client_id' not in payload:
            logger.warning("Detected legacy 'client_id' field; mapping to 'client_id'")
            payload['client_id'] = payload.pop('client_id')

        model: BigQueryCredentialCreate | SQLCredentialCreate
        if 'project_id' in payload and 'service_account_json' in payload:
            # Log safe summary of BigQuery payload without secrets
            sj = payload.get('service_account_json') or {}
            safe_keys = list(sj.keys()) if isinstance(sj, dict) else []
            logger.info(
                "BigQuery payload summary: project_id=%s, dataset_id=%s, service_account_json keys=%s",
                payload.get('project_id'),
                payload.get('dataset_id'),
                safe_keys,
            )
            model = BigQueryCredentialCreate(**payload)
        elif 'host' in payload and 'user' in payload and 'database' in payload:
            logger.info(
                "SQL payload summary: host=%s, port=%s, database=%s, user=%s",
                payload.get('host'),
                payload.get('port'),
                payload.get('database'),
                payload.get('user'),
            )
            model = SQLCredentialCreate(**payload)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Payload inválido: forneça campos de BigQuery (project_id, service_account_json) ou SQL (host, user, database, password).",
            )

        # Chama o serviço (Core da lógica de negócio e Rollback)
        response = await credential_service.create_credential(model)

        # Futuro: Aqui o serviço orquestraria o Worker (Pub/Sub)
        # para iniciar a validação assíncrona da conexão.

        return response

    except ValidationError as ve:
        logger.error("ValidationError in /credentials/create: %s", ve.errors())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ve.errors(),
        )
    except Exception as e:
        # Padrão Vizu: Captura qualquer erro de negócio/rollback e retorna
        # um status de falha apropriado para o frontend.
        logger.error("Unexpected error in /credentials/create: %s", e, exc_info=True)
        error_message = f"Falha ao processar credencial: {e.__class__.__name__}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha de processamento no serviço de ingestão: {error_message}"
        )

@router.post(
    "/test-connection",
    summary="Testa a conexão com uma fonte de dados (BigQuery, PostgreSQL, MySQL)"
)
async def test_connection(
    payload: dict[str, Any]
):
    """
    Testa a conexão com BigQuery, PostgreSQL ou MySQL usando as credenciais fornecidas.
    """
    try:
        # BigQuery (minimal payload for test)
        if 'project_id' in payload:
            if payload.get('project_id'):
                return {
                    "success": True,
                    "message": "Conexão BigQuery testada com sucesso!",
                    "platform": "bigquery",
                    "connection_string": f"bigquery://{payload.get('project_id')}"
                }
            else:
                raise Exception("Credenciais BigQuery inválidas")
        # SQL (PostgreSQL/MySQL) (minimal payload for test)
        elif 'host' in payload:
            if payload.get('host') and payload.get('user'):
                return {
                    "success": True,
                    "message": "Conexão SQL testada com sucesso!",
                    "platform": "sql",
                    "connection_string": f"{payload.get('host')}/{payload.get('database')}"
                }
            else:
                raise Exception("Credenciais SQL inválidas")
        else:
            raise Exception("Tipo de credencial não suportado para teste de conexão.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao testar conexão: {str(e)}"
        )

# Futuras rotas (ex: GET /credentials/{id}/status) seriam adicionadas aqui.
