"""API routes for document uploads."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from standalone_agent_api.api.auth import AuthResult, get_auth_result
from standalone_agent_api.core.service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter()

_session_service: SessionService | None = None


def get_session_service() -> SessionService:
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service


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

        # Read file
        content = await file.read()

        # TODO: Implement document processing
        # 1. Upload to Supabase Storage
        # 2. Trigger process-document Edge Function
        # 3. Wait for embedding completion
        # 4. Add to session's uploaded_document_ids
        # For now, return placeholder

        return DocumentUploadResponse(
            document_id="doc_placeholder",
            file_name=file.filename,
            status="processing",
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
        # TODO: Query session's uploaded_document_ids
        # For now, return empty list
        return []
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
