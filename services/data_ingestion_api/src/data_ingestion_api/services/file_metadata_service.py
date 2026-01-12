"""
Service for managing uploaded file metadata.
"""
import logging
from uuid import UUID
from datetime import datetime

from data_ingestion_api.services import supabase_client
from data_ingestion_api.schemas.connector_schemas import (
    UploadedFileResponse,
    FileListResponse,
)

logger = logging.getLogger(__name__)


class FileMetadataService:
    """Service for file metadata operations."""

    async def get_uploaded_files(self, client_id: str) -> FileListResponse:
        """Get all uploaded files for a client."""
        files = await supabase_client.select(
            table="uploaded_files_metadata",
            columns="*",
            filters={"client_id": client_id},
            client_id=client_id,
        )

        # Sort by uploaded_at descending
        files.sort(key=lambda x: x.get("uploaded_at", datetime.min.isoformat()), reverse=True)

        total_size = sum(f.get("file_size_bytes", 0) for f in files)

        # Generate signed URLs for download
        file_responses = []

        for file in files:
            # Note: Signed URL generation would require Supabase Storage client
            # For now, we'll set download_url to None and implement later if needed
            download_url = None

            file_responses.append(
                UploadedFileResponse(
                    id=UUID(file["id"]),
                    file_name=file["file_name"],
                    file_size_bytes=file["file_size_bytes"],
                    file_type=file.get("file_type"),
                    status=file.get("status", "uploaded"),
                    records_count=file.get("records_count", 0),
                    records_imported=file.get("records_imported", 0),
                    uploaded_at=datetime.fromisoformat(file["uploaded_at"].replace("Z", "+00:00")),
                    processed_at=datetime.fromisoformat(file["processed_at"].replace("Z", "+00:00")) if file.get("processed_at") else None,
                    storage_path=file["storage_path"],
                    download_url=download_url,
                )
            )

        return FileListResponse(
            files=file_responses,
            total_files=len(files),
            total_size_bytes=total_size,
        )

    async def delete_file(self, file_id: UUID, client_id: str) -> bool:
        """
        Delete a file (soft delete: mark as deleted).
        Also deletes from Supabase Storage (to be implemented).
        """
        # 1. Get file metadata
        files = await supabase_client.select(
            table="uploaded_files_metadata",
            columns="*",
            filters={"id": str(file_id), "client_id": client_id},
            client_id=client_id,
        )

        if not files or len(files) == 0:
            raise ValueError(f"File {file_id} not found")

        file = files[0]

        # 2. TODO: Delete from storage
        # storage = get_storage()
        # try:
        #     storage.delete_file(file["storage_path"])
        #     logger.info(f"Deleted file from storage: {file['storage_path']}")
        # except Exception as e:
        #     logger.error(f"Failed to delete file from storage: {e}")

        # 3. Soft delete in database
        await supabase_client.update(
            table="uploaded_files_metadata",
            data={
                "status": "deleted",
                "deleted_at": datetime.utcnow().isoformat(),
            },
            filters={"id": str(file_id)},
        )

        return True

    async def create_file_metadata(
        self,
        client_id: str,
        file_name: str,
        file_size_bytes: int,
        storage_path: str,
        file_type: str = None,
        content_type: str = None,
    ) -> UUID:
        """Create file metadata record after upload."""
        data = {
            "client_id": client_id,
            "file_name": file_name,
            "file_size_bytes": file_size_bytes,
            "storage_path": storage_path,
            "file_type": file_type,
            "content_type": content_type,
            "status": "uploaded",
            "uploaded_at": datetime.utcnow().isoformat(),
        }

        result = await supabase_client.insert("uploaded_files_metadata", data)
        return UUID(result["id"])


# Singleton instance
file_metadata_service = FileMetadataService()
