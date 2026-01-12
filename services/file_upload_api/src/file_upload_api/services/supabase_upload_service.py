"""
Upload Service using Supabase Storage.

Handles file uploads with proper database registration and RLS security.
"""
import logging
import uuid
from datetime import datetime

from fastapi import UploadFile
from opentelemetry import trace

from file_upload_api.schemas.upload_schemas import FileUploadResponse
from vizu_models.enums import TipoFonte
from vizu_supabase_client import SupabaseStorage, get_storage, get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseUploadService:
    """
    Upload service using Supabase Storage with database registration.

    Ensures proper RLS security and data tracking for all uploads.
    """

    def __init__(self, storage: SupabaseStorage | None = None):
        """
        Initialize the upload service.

        Args:
            storage: Optional SupabaseStorage instance (uses default if not provided)
        """
        self._storage = storage
        self._supabase_client = None

    @property
    def storage(self) -> SupabaseStorage:
        """Lazy-load storage client."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    @property
    def supabase_client(self):
        """Lazy-load Supabase client for database operations."""
        if self._supabase_client is None:
            self._supabase_client = get_supabase_client()
        return self._supabase_client

    def _get_current_trace_id(self) -> str | None:
        """
        Capture the Trace ID from the current OpenTelemetry span.
        """
        current_span = trace.get_current_span()
        if not current_span.is_recording():
            return None

        trace_id = current_span.get_span_context().trace_id
        return trace.format_trace_id(trace_id)

    def _register_fonte_de_dados(
        self,
        client_id: uuid.UUID,
        storage_path: str,
        file_name: str,
        content_type: str
    ) -> int:
        """
        Register the uploaded file in the fonte_de_dados table.

        This ensures:
        - Proper tracking of all uploaded files
        - RLS security (only cliente_vizu can access their own files)
        - Metadata for downstream processing

        Args:
            client_id: UUID of the client
            storage_path: Full path in Supabase Storage
            file_name: Original filename
            content_type: MIME type

        Returns:
            ID of the created fonte_de_dados record
        """
        logger.info(f"Registering fonte_de_dados for {storage_path}")

        data = {
            "client_id": str(client_id),
            "tipo_fonte": TipoFonte.UPLOAD.value,  # Or use the string value directly
            "caminho": storage_path,
            "nome_arquivo": file_name,
            "content_type": content_type,
            "data_upload": datetime.utcnow().isoformat(),
            "status": "PENDENTE_PROCESSAMENTO"
        }

        response = self.supabase_client.table("fonte_de_dados").insert(data).execute()

        if not response.data:
            raise ValueError("Failed to register fonte_de_dados in database")

        fonte_id = response.data[0]["id"]
        logger.info(f"fonte_de_dados registered with ID: {fonte_id}")

        return fonte_id

    def process_upload(
        self, file: UploadFile, client_id: uuid.UUID
    ) -> FileUploadResponse:
        """
        Process file upload with full RLS security and database registration:
        1. Generate unique IDs
        2. Upload file to Supabase Storage (RLS-protected bucket)
        3. Register in fonte_de_dados table (RLS-protected)
        4. Return response with tracking IDs

        RLS Security:
        - Supabase Storage bucket policies enforce client_id access
        - Database RLS policies on fonte_de_dados table enforce tenant isolation
        """
        logger.info(
            f"Starting upload processing for client_id: {client_id}"
        )

        # 1. Generate IDs
        job_id = uuid.uuid4()

        # 2. Capture Trace ID for observability
        trace_id = self._get_current_trace_id()

        # 3. Upload to Supabase Storage
        try:
            # Read file content
            file_content = file.file.read()

            logger.info(f"Job [{job_id}]: Uploading to Supabase Storage...")

            result = self.storage.upload_file_for_cliente(
                file_content=file_content,
                filename=file.filename,
                cliente_id=client_id,
                content_type=file.content_type,
                job_id=job_id,
            )

            logger.info(f"Job [{job_id}]: Upload complete at {result.path}")

        except Exception as e:
            logger.error(f"Job [{job_id}]: Storage upload failed. Error: {e}")
            raise

        # 4. Register in database (with RLS security)
        try:
            fonte_id = self._register_fonte_de_dados(
                client_id=client_id,
                storage_path=result.full_path,
                file_name=file.filename,
                content_type=file.content_type or "application/octet-stream"
            )
        except Exception as e:
            # Rollback: Delete the uploaded file if database registration fails
            logger.error(f"Job [{job_id}]: Database registration failed. Rolling back storage upload.")
            try:
                self.storage.delete_file(result.path)
                logger.info(f"Job [{job_id}]: Storage file deleted successfully")
            except Exception as rollback_error:
                logger.error(f"Job [{job_id}]: CRITICAL - Failed to delete file during rollback: {rollback_error}")

            raise Exception(f"Failed to register upload in database: {e}")

        # 5. Return response schema
        return FileUploadResponse(
            job_id=job_id,
            file_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
            storage_path=result.full_path,
            fonte_de_dados_id=fonte_id
        )


# Factory function for dependency injection
def get_supabase_upload_service() -> SupabaseUploadService:
    """
    Factory function to create SupabaseUploadService.

    Use this with FastAPI's Depends() for dependency injection.
    """
    return SupabaseUploadService()
