import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from file_upload_api.api.dependencies import (
    get_cliente_vizu_id_from_token,
)
from file_upload_api.core.config import Settings, get_settings
from file_upload_api.schemas.upload_schemas import FileUploadResponse
from file_upload_api.services.supabase_upload_service import (
    SupabaseUploadService,
    get_supabase_upload_service,
)

# --- Inicialização ---
logger = logging.getLogger(__name__)
api_router = APIRouter(
    tags=["File Upload"],
)


# --- Endpoints da API ---


@api_router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recebe um arquivo e enfileira para processamento assíncrono.",
)
def upload_file(
    # Dependência de Autenticação
    cliente_vizu_id: uuid.UUID = Depends(get_cliente_vizu_id_from_token),
    # Dependência do Arquivo (requer python-multipart)
    file: UploadFile = File(..., description="O arquivo a ser processado."),
    # Dependência da Lógica de Negócio (usando Supabase Storage)
    service: SupabaseUploadService = Depends(get_supabase_upload_service),
):
    """
    Recebe um arquivo (via multipart/form-data) para um cliente Vizu autenticado.

    O serviço irá:
    1. Autenticar o cliente (via `get_cliente_vizu_id_from_token`).
    2. Fazer o upload do arquivo para Supabase Storage.
    3. Retornar um ID de job e os metadados do arquivo.

    O processamento real (parsing, embedding, etc.) pode ser feito
    via database triggers ou polling do bucket.
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
        logger.error(
            f"Erro ao processar upload para {cliente_vizu_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar o arquivo. Erro: {e.__class__.__name__}",
        )
