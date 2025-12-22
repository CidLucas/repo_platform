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

    content_type: str = Field(
        ..., description="O MIME type do arquivo detectado pelo servidor."
    )

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
