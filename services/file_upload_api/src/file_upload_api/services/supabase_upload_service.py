"""
Upload Service using Supabase Storage.

Replaces GCS/Pub/Sub with Supabase Storage for simpler deployment.
"""
import logging
import uuid

from fastapi import UploadFile
from opentelemetry import trace

from file_upload_api.schemas.upload_schemas import FileUploadResponse
from vizu_supabase_client import SupabaseStorage, get_storage

logger = logging.getLogger(__name__)


class SupabaseUploadService:
    """
    Upload service using Supabase Storage.
    
    Simplified version that doesn't require GCS or Pub/Sub.
    For async processing, we can use Supabase Database triggers or 
    a separate polling mechanism.
    """

    def __init__(self, storage: SupabaseStorage | None = None):
        """
        Initialize the upload service.
        
        Args:
            storage: Optional SupabaseStorage instance (uses default if not provided)
        """
        self._storage = storage

    @property
    def storage(self) -> SupabaseStorage:
        """Lazy-load storage client."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def _get_current_trace_id(self) -> str | None:
        """
        Capture the Trace ID from the current OpenTelemetry span.
        """
        current_span = trace.get_current_span()
        if not current_span.is_recording():
            return None

        trace_id = current_span.get_span_context().trace_id
        return trace.format_trace_id(trace_id)

    def process_upload(
        self, file: UploadFile, cliente_vizu_id: uuid.UUID
    ) -> FileUploadResponse:
        """
        Process file upload:
        1. Generate unique IDs
        2. Capture Trace ID
        3. Upload file to Supabase Storage
        4. Return response schema
        
        Note: For async processing, consider using:
        - Supabase Database triggers on storage.objects table
        - A separate worker that polls for new files
        - Supabase Edge Functions
        """
        logger.info(
            f"Starting upload processing for cliente_vizu_id: {cliente_vizu_id}"
        )

        # 1. Generate IDs
        job_id = uuid.uuid4()

        # 2. Capture Trace ID
        trace_id = self._get_current_trace_id()

        # 3. Upload to Supabase Storage
        try:
            # Read file content
            file_content = file.file.read()
            
            logger.info(f"Job [{job_id}]: Uploading to Supabase Storage...")
            
            result = self.storage.upload_file_for_cliente(
                file_content=file_content,
                filename=file.filename,
                cliente_id=cliente_vizu_id,
                content_type=file.content_type,
                job_id=job_id,
            )
            
            logger.info(f"Job [{job_id}]: Upload complete at {result.path}")

        except Exception as e:
            logger.error(f"Job [{job_id}]: Upload failed. Error: {e}")
            raise

        # 4. Return response schema
        # Note: gcs_path field is kept for backward compatibility
        return FileUploadResponse(
            job_id=job_id,
            file_name=file.filename,
            content_type=file.content_type,
            gcs_path=result.full_path,  # Now points to Supabase path
        )


# Factory function for dependency injection
def get_supabase_upload_service() -> SupabaseUploadService:
    """
    Factory function to create SupabaseUploadService.
    
    Use this with FastAPI's Depends() for dependency injection.
    """
    return SupabaseUploadService()
