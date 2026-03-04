import logging
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from file_upload_api.api.dependencies import (
    get_client_id_from_token,
)
from file_upload_api.core.config import Settings, get_settings
from file_upload_api.schemas.upload_schemas import (
    FileUploadResponse,
    ProcessRequest,
    ProcessResponse,
)
from file_upload_api.services.processing_service import (
    DocumentProcessingService,
    get_processing_service,
)
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
    client_id: uuid.UUID = Depends(get_client_id_from_token),
    # Dependência do Arquivo (requer python-multipart)
    file: UploadFile = File(..., description="O arquivo a ser processado."),
    # Dependência da Lógica de Negócio (usando Supabase Storage)
    service: SupabaseUploadService = Depends(get_supabase_upload_service),
):
    """
    Recebe um arquivo (via multipart/form-data) para um cliente Vizu autenticado.

    O serviço irá:
    1. Autenticar o cliente (via `get_client_id_from_token`).
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
        logger.info(f"Recebida requisição de upload de {client_id} para o arquivo: {file.filename}")

        # Chama a camada de serviço modularizada
        response_data = service.process_upload(file=file, client_id=client_id)

        return response_data

    except Exception as e:
        logger.error(f"Erro ao processar upload para {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar o arquivo. Erro: {e.__class__.__name__}",
        )


@api_router.post(
    "/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Processa um arquivo complexo já armazenado no Supabase Storage.",
)
async def process_uploaded_file(
    request_body: ProcessRequest,
    background_tasks: BackgroundTasks,
    client_id: uuid.UUID = Depends(get_client_id_from_token),
    service: DocumentProcessingService = Depends(get_processing_service),
):
    """Process a file already uploaded to Supabase Storage.

    Used for complex files that need Python-side processing (docling):
    scanned PDFs, PPTX, XLSX, or any file where the user selected
    "advanced processing".

    Simple files (TXT, CSV, MD, text-based PDFs) are handled by
    the process-document Edge Function instead.

    The processing runs as a background task:
    1. Downloads the file from Storage (knowledge-base bucket)
    2. Parses with docling (OCR, table extraction, layout analysis)
    3. Chunks the extracted text
    4. Inserts chunks into vector_db.document_chunks (no embedding)
    5. pgmq trigger queues chunks → embed Edge Function handles embedding
    6. Updates document status in vector_db.documents
    """
    # Validate client_id matches the authenticated user
    if str(client_id) != request_body.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client ID in request body does not match authenticated user.",
        )

    logger.info(
        f"Processing request for document {request_body.document_id} from client {client_id}"
    )

    # Run processing in background — return 202 immediately
    background_tasks.add_task(
        service.process_document,
        document_id=request_body.document_id,
        storage_path=request_body.storage_path,
        file_name=request_body.file_name,
        client_id=request_body.client_id,
    )

    return ProcessResponse(
        document_id=request_body.document_id,
        status="processing",
        message="Document processing started in background.",
    )
