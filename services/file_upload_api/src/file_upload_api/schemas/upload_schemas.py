import uuid

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """
    Schema da resposta retornada ao cliente após um upload bem-sucedido.

    Fornece ao cliente um ID de rastreamento (job_id) e confirmação
    dos dados recebidos.
    """

    job_id: uuid.UUID = Field(
        ...,
        description="O ID único para esta tarefa de processamento. Pode ser usado para rastrear o status (em implementações futuras).",
    )

    file_name: str = Field(..., description="O nome original do arquivo enviado.")

    content_type: str = Field(..., description="O MIME type do arquivo detectado pelo servidor.")

    storage_path: str = Field(
        ...,
        description="O caminho no Supabase Storage onde o arquivo foi armazenado.",
    )

    fonte_de_dados_id: int = Field(
        ...,
        description="ID do registro na tabela fonte_de_dados que representa este arquivo.",
    )

    class Config:
        # Padrão Pydantic V2 (permite que o schema seja criado a partir
        # de atributos de um objeto, não apenas dicts)
        from_attributes = True


# ---------------------------------------------------------------------------
# Schemas for the /process endpoint (complex file processing via docling)
# ---------------------------------------------------------------------------


class ProcessRequest(BaseModel):
    """Request body for the /v1/upload/process endpoint.

    The file must already be uploaded to Supabase Storage (knowledge-base bucket).
    This endpoint triggers Python-side parsing with docling for complex documents.
    """

    document_id: str = Field(
        ...,
        description="UUID of the document record in vector_db.documents.",
    )
    storage_path: str = Field(
        ...,
        description="Path of the file in the knowledge-base Storage bucket.",
    )
    file_name: str = Field(
        ...,
        description="Original filename (used for parser selection).",
    )
    client_id: str = Field(
        ...,
        description="UUID of the client who owns the document.",
    )


class ProcessResponse(BaseModel):
    """Response body for the /v1/upload/process endpoint."""

    document_id: str = Field(
        ...,
        description="UUID of the document being processed.",
    )
    status: str = Field(
        default="processing",
        description="Current processing status (processing, completed, failed).",
    )
    message: str = Field(
        default="Document processing started in background.",
        description="Human-readable status message.",
    )
