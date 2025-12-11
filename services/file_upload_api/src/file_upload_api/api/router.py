import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,  # <-- Usado para acessar o app.state
    UploadFile,
    status,
)

# Clientes GCP para injeção
from google.cloud import storage
from google.cloud.pubsub_v1 import PublisherClient

from file_upload_api.api.dependencies import (
    get_cliente_vizu_id_from_token,
)  # (Dependência de autenticação)

# Componentes locais da nossa aplicação
from file_upload_api.core.config import Settings, get_settings
from file_upload_api.schemas.upload_schemas import FileUploadResponse
from file_upload_api.services.upload_service import UploadService

# --- Inicialização ---
logger = logging.getLogger(__name__)
api_router = APIRouter(
    tags=["File Upload"],
)

# --- Funções de Fábrica de Dependências (Padrão Vizu: Injeção de Dependência) ---


def get_gcp_storage_client(request: Request) -> storage.Client:
    """
    Obtém o cliente GCS singleton do estado da aplicação (inicializado no 'lifespan').

    (Se não estiver no 'lifespan', cria um novo. Mas o ideal é usar o 'lifespan')
    """
    if hasattr(request.app.state, "storage_client"):
        logger.debug("Usando cliente GCS singleton do app.state")
        return request.app.state.storage_client

    logger.warning("Criando novo cliente GCS (não encontrado no app.state).")
    return storage.Client()


def get_gcp_publisher_client(request: Request) -> PublisherClient:
    """
    Obtém o cliente Pub/Sub singleton do estado da aplicação (inicializado no 'lifespan').
    """
    if hasattr(request.app.state, "publisher_client"):
        logger.debug("Usando cliente Pub/Sub singleton do app.state")
        return request.app.state.publisher_client

    logger.warning("Criando novo cliente Pub/Sub (não encontrado no app.state).")
    return PublisherClient()


def get_upload_service(
    settings: Settings = Depends(get_settings),
    storage_client: storage.Client = Depends(get_gcp_storage_client),
    publisher_client: PublisherClient = Depends(get_gcp_publisher_client),
) -> UploadService:
    """
    Função de fábrica para injetar o UploadService com todas as suas dependências.

    Este é o núcleo da nossa Testabilidade: podemos mockar esta função
    para injetar um UploadService falso nos testes.
    """
    return UploadService(
        storage_client=storage_client,
        publisher_client=publisher_client,
        settings=settings,
    )


# --- Endpoints da API ---


@api_router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recebe um arquivo e enfileira para processamento assíncrono.",
)
def upload_file(
    # Dependência de Autenticação (deve ser implementada)
    cliente_vizu_id: uuid.UUID = Depends(get_cliente_vizu_id_from_token),
    # Dependência do Arquivo (requer python-multipart)
    file: UploadFile = File(..., description="O arquivo a ser processado."),
    # Dependência da Lógica de Negócio (Padrão Vizu: Modularização)
    service: UploadService = Depends(get_upload_service),
):
    """
    Recebe um arquivo (via multipart/form-data) para um cliente Vizu autenticado.

    O serviço irá:
    1. Autenticar o cliente (via `get_cliente_vizu_id_from_token`).
    2. Fazer o upload do arquivo bruto para um bucket GCS seguro.
    3. Publicar uma mensagem de "job" em um tópico Pub/Sub.
    4. Retornar um ID de job e os metadados do arquivo.

    O processamento real (parsing, embedding, etc.) é feito
    de forma assíncrona pelo `file_processing_worker`.
    """
    if not file.filename or not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido. 'filename' e 'content_type' são obrigatórios.",
        )

    try:
        logger.info(
            f"Recebida requisição de upload de {cliente_vizu_id} para o arquivo: {file.filename}"
        )

        # Chama a camada de serviço modularizada
        response_data = service.process_upload(
            file=file, cliente_vizu_id=cliente_vizu_id
        )

        return response_data

    except Exception as e:
        # Padrão de tratamento de erro
        logger.error(
            f"Erro ao processar upload para {cliente_vizu_id}: {e}", exc_info=True
        )
        # TODO: Implementar tratamento de exceções customizadas (ex: GCSUploadError, PubSubPublishError)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar o arquivo. Erro: {e.__class__.__name__}",
        )
