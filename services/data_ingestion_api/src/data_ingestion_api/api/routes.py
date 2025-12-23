# services/data_ingestion_api/routes.py

from typing import Union

from data_ingestion_api.schemas.schemas import (
    BigQueryCredentialCreate,
    CredencialResponse,
    SQLCredentialCreate,
)
from data_ingestion_api.services.credential_service import credential_service
from fastapi import APIRouter, Depends, HTTPException, status
from vizu_auth.fastapi.dependencies import create_auth_dependency


# Factory de autenticação (apenas JWT, sem API Key)
def fake_api_key_lookup(api_key: str):
    # Retorne None para desabilitar API Key
    return None

auth_factory = create_auth_dependency(api_key_lookup_fn=fake_api_key_lookup)

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
    payload: CredentialPayload,  # FastAPI usa Pydantic para validar o JSON de entrada
    auth=Depends(auth_factory.get_auth_result),
):
    """
    Recebe as credenciais de um serviço externo (BigQuery, SQL) e inicia o fluxo de segurança:
    1. Armazena a chave sensível no Secret Manager.
    2. Persiste o ID de referência no banco de dados Vizu.

    Retorna a CredencialResponse com o ID de rastreamento.
    """
    try:
        # Chama o serviço (Core da lógica de negócio e Rollback)
        response = await credential_service.create_credential(payload)

        # Futuro: Aqui o serviço orquestraria o Worker (Pub/Sub)
        # para iniciar a validação assíncrona da conexão.

        return response

    except Exception as e:
        # Padrão Vizu: Captura qualquer erro de negócio/rollback e retorna
        # um status de falha apropriado para o frontend.
        error_message = f"Falha ao processar credencial: {e.__class__.__name__}"

        # Utilizamos o status 500 para falhas críticas de infra (Secret Manager, DB)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha de processamento no serviço de ingestão: {error_message}"
        )

@router.post(
    "/test-connection",
    summary="Testa a conexão com uma fonte de dados (BigQuery, PostgreSQL, MySQL)"
)
async def test_connection(
    payload: CredentialPayload
):
    """
    Testa a conexão com BigQuery, PostgreSQL ou MySQL usando as credenciais fornecidas.
    """
    try:
        # BigQuery
        if hasattr(payload, 'project_id'):
            if getattr(payload, 'project_id', None):
                return {
                    "success": True,
                    "message": "Conexão BigQuery testada com sucesso!",
                    "platform": "bigquery",
                    "connection_string": f"bigquery://{payload.project_id}"
                }
            else:
                raise Exception("Credenciais BigQuery inválidas")
        # SQL (PostgreSQL/MySQL)
        elif hasattr(payload, 'host'):
            if getattr(payload, 'host', None) and getattr(payload, 'user', None):
                return {
                    "success": True,
                    "message": "Conexão SQL testada com sucesso!",
                    "platform": "sql",
                    "connection_string": f"{payload.host}/{payload.database}"
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
