"""
Supabase Storage - Helper for file upload/download operations.

Uses Supabase Storage API instead of GCS for file operations.
"""
import logging
import uuid
from dataclasses import dataclass
from typing import BinaryIO

from .client import get_supabase_client

logger = logging.getLogger(__name__)

# Default bucket for file uploads
DEFAULT_BUCKET = "file-uploads"


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    bucket: str
    path: str
    full_path: str
    public_url: str | None = None


@dataclass
class StorageConfig:
    """Configuration for storage operations."""
    bucket: str = DEFAULT_BUCKET
    max_file_size: int = 100 * 1024 * 1024  # 100MB default


class SupabaseStorage:
    """
    Helper class for Supabase Storage operations.

    Usage:
        storage = SupabaseStorage()
        result = storage.upload_file(file_content, "path/to/file.pdf", "application/pdf")
        url = storage.get_signed_url(result.path)
    """

    def __init__(self, bucket: str = DEFAULT_BUCKET):
        self.bucket = bucket
        self._client = None

    @property
    def client(self):
        """Lazy-load the Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def storage(self):
        """Get the storage client for the configured bucket."""
        return self.client.storage.from_(self.bucket)

    def upload_file(
        self,
        file_content: bytes | BinaryIO,
        path: str,
        content_type: str | None = None,
        upsert: bool = False,
    ) -> UploadResult:
        """
        Upload a file to Supabase Storage.

        Args:
            file_content: File bytes or file-like object
            path: Path within the bucket (e.g., "cliente_id/filename.pdf")
            content_type: MIME type of the file
            upsert: If True, overwrite existing file

        Returns:
            UploadResult with path and URL info
        """
        options = {}
        if content_type:
            options["content-type"] = content_type
        if upsert:
            options["upsert"] = "true"

        # If file_content is a file-like object, read it
        if hasattr(file_content, 'read'):
            file_content = file_content.read()

        logger.info(f"Uploading file to {self.bucket}/{path}")

        response = self.storage.upload(path, file_content, options)

        logger.info(f"Upload complete: {path}")

        return UploadResult(
            bucket=self.bucket,
            path=path,
            full_path=f"{self.bucket}/{path}",
        )

    def upload_file_for_cliente(
        self,
        file_content: bytes | BinaryIO,
        filename: str,
        cliente_id: str | uuid.UUID,
        content_type: str | None = None,
        job_id: str | uuid.UUID | None = None,
    ) -> UploadResult:
        """
        Upload a file with standard Vizu path convention: {cliente_id}/{job_id}-{filename}

        Args:
            file_content: File bytes or file-like object
            filename: Original filename
            cliente_id: UUID of the cliente_vizu
            content_type: MIME type
            job_id: Optional job ID (generated if not provided)

        Returns:
            UploadResult with path info
        """
        if job_id is None:
            job_id = uuid.uuid4()

        # Standard path: {cliente_id}/{job_id}-{filename}
        path = f"{cliente_id}/{job_id}-{filename}"

        return self.upload_file(file_content, path, content_type)

    def download_file(self, path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            path: Path within the bucket

        Returns:
            File content as bytes
        """
        logger.info(f"Downloading file from {self.bucket}/{path}")
        response = self.storage.download(path)
        return response

    def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Get a signed URL for temporary access to a file.

        Args:
            path: Path within the bucket
            expires_in: URL expiration time in seconds (default 1 hour)

        Returns:
            Signed URL string
        """
        response = self.storage.create_signed_url(path, expires_in)
        return response.get("signedURL") or response.get("signedUrl")

    def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: Path within the bucket

        Returns:
            True if deleted successfully
        """
        logger.info(f"Deleting file from {self.bucket}/{path}")
        self.storage.remove([path])
        return True

    def list_files(self, prefix: str = "", limit: int = 100) -> list[dict]:
        """
        List files in the bucket.

        Args:
            prefix: Path prefix to filter by
            limit: Maximum number of files to return

        Returns:
            List of file metadata dicts
        """
        response = self.storage.list(prefix, {"limit": limit})
        return response

    def move_file(self, from_path: str, to_path: str) -> bool:
        """
        Move/rename a file within the bucket.

        Args:
            from_path: Current path
            to_path: New path

        Returns:
            True if moved successfully
        """
        logger.info(f"Moving file from {from_path} to {to_path}")
        self.storage.move(from_path, to_path)
        return True


# Singleton instance
_storage_instance: SupabaseStorage | None = None


def get_storage(bucket: str = DEFAULT_BUCKET) -> SupabaseStorage:
    """
    Get a SupabaseStorage instance.

    Args:
        bucket: Bucket name (default: file-uploads)

    Returns:
        SupabaseStorage instance
    """
    global _storage_instance

    if _storage_instance is None or _storage_instance.bucket != bucket:
        _storage_instance = SupabaseStorage(bucket)

    return _storage_instance
