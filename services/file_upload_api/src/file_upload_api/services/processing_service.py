"""Service for processing complex files (docling) that are already in Supabase Storage.

Downloads the file from Storage → parses with vizu_parsers (docling for complex
formats) → chunks → inserts into vector_db.document_chunks (without embedding).
The pgmq queue + embed Edge Function handles embedding asynchronously.
"""

import logging
from io import BytesIO

from vizu_parsers.chunker.models import Chunk
from vizu_parsers.pipeline import parse_and_chunk
from vizu_supabase_client import get_storage, get_supabase_client

logger = logging.getLogger(__name__)

# Batch size for bulk inserts into vector_db.document_chunks
INSERT_BATCH_SIZE = 100

# Storage bucket for knowledge base files
KNOWLEDGE_BASE_BUCKET = "knowledge-base"


class DocumentProcessingService:
    """Processes complex files: download from Storage → parse with docling → chunk → insert to vector_db."""

    def __init__(self) -> None:
        self._client = None
        self._storage = None

    @property
    def client(self):
        """Lazy-load Supabase client (service_role for DB writes)."""
        if self._client is None:
            self._client = get_supabase_client(use_service_role=True)
        return self._client

    @property
    def storage(self):
        """Lazy-load Storage client for knowledge-base bucket."""
        if self._storage is None:
            self._storage = get_storage(bucket=KNOWLEDGE_BASE_BUCKET)
        return self._storage

    def _update_document_status(
        self,
        document_id: str,
        status: str,
        *,
        chunk_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update document status in vector_db.documents."""
        data: dict = {"status": status}
        if chunk_count is not None:
            data["chunk_count"] = chunk_count
        if error_message is not None:
            data["error_message"] = error_message

        self.client.schema("vector_db").table("documents").update(data).eq(
            "id", document_id
        ).execute()

        logger.info(f"Document {document_id} status → {status}")

    def _insert_chunks_batch(
        self,
        chunks: list[Chunk],
        document_id: str,
        client_id: str,
        file_name: str,
    ) -> int:
        """Insert chunks into vector_db.document_chunks in batches.

        Chunks are inserted WITHOUT embedding — the pgmq trigger
        queues them for the embed Edge Function automatically.

        Returns:
            Total number of chunks inserted.
        """
        total = 0
        records = [
            {
                "document_id": document_id,
                "client_id": client_id,
                "content": chunk.text,
                "chunk_index": chunk.index,
                "metadata": {
                    "source_file": file_name,
                    **(chunk.metadata or {}),
                },
                # embedding is NULL → trigger queues to pgmq → embed Edge Function
            }
            for chunk in chunks
        ]

        for i in range(0, len(records), INSERT_BATCH_SIZE):
            batch = records[i : i + INSERT_BATCH_SIZE]
            self.client.schema("vector_db").table("document_chunks").insert(batch).execute()
            total += len(batch)
            logger.debug(f"Inserted chunk batch {i // INSERT_BATCH_SIZE + 1} ({len(batch)} chunks)")

        return total

    async def process_document(
        self,
        document_id: str,
        storage_path: str,
        file_name: str,
        client_id: str,
    ) -> dict:
        """Process a complex file end-to-end.

        Pipeline:
        1. Update document status to 'processing'
        2. Download file from Supabase Storage
        3. Parse and chunk using vizu_parsers (docling for complex formats)
        4. Batch insert chunks into vector_db.document_chunks (no embedding)
        5. Update document status to 'completed'

        The pgmq trigger on document_chunks automatically queues
        embedding jobs for the embed Edge Function.

        Args:
            document_id: UUID of the document record in vector_db.documents.
            storage_path: Path in the knowledge-base Storage bucket.
            file_name: Original filename for parser selection.
            client_id: UUID of the owning client.

        Returns:
            Dict with status and chunk_count.
        """
        # 1. Mark as processing
        self._update_document_status(document_id, "processing")

        try:
            # 2. Download file from Storage
            logger.info(f"Downloading {file_name} from storage: {storage_path}")
            file_bytes = self.storage.download_file(storage_path)
            file_stream = BytesIO(file_bytes)

            # 3. Parse and chunk
            logger.info(f"Parsing and chunking {file_name}...")
            chunks = parse_and_chunk(
                file_stream=file_stream,
                filename=file_name,
                chunk_size=500,
                chunk_overlap=50,
            )

            if not chunks:
                self._update_document_status(
                    document_id,
                    "failed",
                    error_message="No text could be extracted from the document.",
                )
                return {"status": "failed", "chunk_count": 0}

            # 4. Batch insert chunks
            logger.info(f"Inserting {len(chunks)} chunks for document {document_id}")
            total_inserted = self._insert_chunks_batch(
                chunks=chunks,
                document_id=document_id,
                client_id=client_id,
                file_name=file_name,
            )

            # 5. Mark as completed
            self._update_document_status(document_id, "completed", chunk_count=total_inserted)

            logger.info(f"Document {document_id} processed: {total_inserted} chunks created")
            return {"status": "completed", "chunk_count": total_inserted}

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)
            self._update_document_status(
                document_id,
                "failed",
                error_message=str(e)[:500],  # Truncate long error messages
            )
            raise


def get_processing_service() -> DocumentProcessingService:
    """Factory function for FastAPI dependency injection."""
    return DocumentProcessingService()
