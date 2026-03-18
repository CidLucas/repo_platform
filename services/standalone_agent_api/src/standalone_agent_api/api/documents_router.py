"""API routes for document uploads."""

import asyncio
import logging
import pathlib
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from standalone_agent_api.api.auth import AuthResult, get_auth_result
from standalone_agent_api.core.service import SessionService
from vizu_supabase_client import get_storage, get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration
KNOWLEDGE_BASE_BUCKET = "knowledge-base"
MAX_EMBEDDING_WAIT_TIME = 30  # seconds
EMBEDDING_POLL_INTERVAL = 0.5  # seconds

_session_service: SessionService | None = None


def get_session_service() -> SessionService:
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service


async def _upload_to_storage(
    client_id: str,
    document_id: str,
    file_content: bytes,
    file_name: str,
) -> str:
    """
    Upload file to Supabase Storage.

    Returns:
        storage_path: Path within the knowledge-base bucket
    """
    try:
        storage = get_storage(bucket=KNOWLEDGE_BASE_BUCKET)
        storage_path = f"{client_id}/{document_id}-{file_name}"

        logger.info(f"Uploading document {document_id} to storage: {storage_path}")
        storage.upload_file(file_content, storage_path)

        return storage_path
    except Exception as e:
        logger.error(f"Error uploading to storage: {e}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")


async def _create_document_record(
    client_id: str,
    document_id: str,
    file_name: str,
    file_type: str,
    storage_path: str,
) -> dict:
    """
    Create document record in vector_db.documents table.

    Returns:
        Document record from database
    """
    try:
        db = get_supabase_client()

        logger.info(f"Creating document record: {document_id}")
        result = db.schema("vector_db").table("documents").insert({
            "id": document_id,
            "client_id": client_id,
            "file_name": file_name,
            "file_type": file_type,
            "storage_path": storage_path,
            "source": "upload",
            "processing_mode": "simple",
            "status": "processing",
            "scope": "client",
        }).execute()

        if not result.data:
            raise ValueError("Failed to create document record")

        return result.data[0]
    except Exception as e:
        logger.error(f"Error creating document record: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {str(e)}")


async def _invoke_process_document(
    document_id: str,
    storage_path: str,
    client_id: str,
    file_name: str,
    file_type: str,
) -> dict:
    """
    Invoke the process-document Edge Function.

    Returns:
        Response from the Edge Function
    """
    try:
        db = get_supabase_client()

        logger.info(f"Invoking process-document Edge Function for {document_id}")
        response = db.functions.invoke(
            "process-document",
            invoke_options={
                "body": {
                    "document_id": document_id,
                    "storage_path": storage_path,
                    "client_id": client_id,
                    "file_name": file_name,
                    "file_type": file_type,
                }
            }
        )

        return response
    except Exception as e:
        logger.error(f"Error invoking process-document: {e}")
        raise HTTPException(status_code=500, detail=f"Edge Function invocation failed: {str(e)}")


async def _wait_for_embedding_completion(
    document_id: str,
    max_wait_time: int = MAX_EMBEDDING_WAIT_TIME,
) -> str:
    """
    Poll the document status until embedding is completed or timeout.

    Returns:
        Final status of the document
    """
    db = get_supabase_client()
    elapsed = 0

    while elapsed < max_wait_time:
        result = db.schema("vector_db").table("documents").select("status").eq("id", document_id).execute()

        if result.data:
            status = result.data[0].get("status", "processing")
            logger.info(f"Document {document_id} status: {status}")

            if status in ["completed", "failed"]:
                return status

        await asyncio.sleep(EMBEDDING_POLL_INTERVAL)
        elapsed += EMBEDDING_POLL_INTERVAL

    logger.warning(f"Embedding completion wait timeout for document {document_id}")
    return "processing"  # Still processing, but we're returning for client response



class DocumentUploadResponse(BaseModel):
    """Response from document upload."""

    document_id: str
    file_name: str
    status: str
    size_bytes: int


@router.post("/sessions/{session_id}/documents", response_model=DocumentUploadResponse)
async def upload_document(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    file: UploadFile = File(...),
    session_service: SessionService = Depends(get_session_service),
):
    """Upload document file to session (PDF, TXT, DOCX, etc)."""
    try:
        # Validate file type
        allowed_extensions = (".txt", ".md", ".pdf", ".docx", ".doc")
        if not any(file.filename.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Only {', '.join(allowed_extensions)} files allowed",
            )

        # Read file content
        content = await file.read()

        # Generate unique document ID
        document_id = str(uuid4())

        # Extract file type from filename
        file_type = pathlib.Path(file.filename).suffix.lstrip('.').lower()

        # Step 1: Upload to Supabase Storage
        logger.info(f"Step 1: Uploading document {document_id} for session {session_id}")
        storage_path = await _upload_to_storage(
            client_id=auth_result.client_id,
            document_id=document_id,
            file_content=content,
            file_name=file.filename,
        )

        # Step 2: Create document record in database
        logger.info(f"Step 2: Creating document record")
        doc_record = await _create_document_record(
            client_id=auth_result.client_id,
            document_id=document_id,
            file_name=file.filename,
            file_type=file_type,
            storage_path=storage_path,
        )

        # Step 3: Invoke process-document Edge Function
        logger.info(f"Step 3: Invoking process-document Edge Function")
        await _invoke_process_document(
            document_id=document_id,
            storage_path=storage_path,
            client_id=auth_result.client_id,
            file_name=file.filename,
            file_type=file_type,
        )

        # Step 4: Wait for embedding completion
        logger.info(f"Step 4: Waiting for embedding completion")
        final_status = await _wait_for_embedding_completion(document_id)

        # Step 5: Add to session's uploaded_document_ids
        logger.info(f"Step 5: Linking document to session")
        await session_service.link_document_to_session(
            client_id=auth_result.client_id,
            session_id=session_id,
            document_id=document_id,
        )

        logger.info(f"Document {document_id} successfully processed and linked to session")
        return DocumentUploadResponse(
            document_id=document_id,
            file_name=file.filename,
            status=final_status,
            size_bytes=len(content),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/documents")
async def list_session_documents(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """List document files uploaded to session."""
    try:
        db = get_supabase_client()

        # Get session's uploaded_document_ids
        session_result = db.table("standalone_agent_sessions").select(
            "uploaded_document_ids"
        ).eq("id", session_id).eq("client_id", str(auth_result.client_id)).execute()

        if not session_result.data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        document_ids = session_result.data[0].get("uploaded_document_ids", [])

        if not document_ids:
            return []

        # Query documents from vector_db.documents
        docs_result = db.schema("vector_db").table("documents").select(
            "id,file_name,file_type,storage_path,status,created_at,updated_at"
        ).in_("id", document_ids).execute()

        return docs_result.data or []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LinkDocumentRequest(BaseModel):
    """Request body for linking a document to a session."""
    document_id: str


@router.post("/sessions/{session_id}/documents/link")
async def link_document_to_session(
    session_id: str,
    body: LinkDocumentRequest,
    auth_result: AuthResult = Depends(get_auth_result),
    session_service: SessionService = Depends(get_session_service),
):
    """Link a document (uploaded via knowledge base service) to this session."""
    try:
        result = await session_service.link_document_to_session(
            client_id=auth_result.client_id,
            session_id=session_id,
            document_id=body.document_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking document to session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
