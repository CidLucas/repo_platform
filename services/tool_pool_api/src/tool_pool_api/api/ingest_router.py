"""ingest_router.py

REST endpoint for ingesting complex documents (PPTX, XLSX, scanned PDFs)
that require Docling parsing before being sent to the process-document Edge Function.

Replaces the deprecated file_upload_api /process endpoint.
Flow: request -> Docling (via blu_parsers) -> extracted text -> process-document EF.
"""

import io
import logging
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from blu_auth.core.models import AuthResult
from blu_auth.fastapi.dependencies import get_auth_result

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/ingest", tags=["Document Ingestion"])

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PROCESS_DOCUMENT_EF_URL = f"{SUPABASE_URL}/functions/v1/process-document"


def get_client_id_from_token(auth: AuthResult = Depends(get_auth_result)) -> UUID:
    """Resolve authenticated client_id from JWT token."""
    return auth.client_id


class IngestRequest(BaseModel):
    document_id: str
    storage_path: str
    file_name: str
    file_type: str  # pptx, xlsx, pdf (for OCR path)
    client_id: str
    target_tokens: int | None = None


class IngestResponse(BaseModel):
    document_id: str
    status: str
    message: str


@router.post("/document", response_model=IngestResponse, status_code=status.HTTP_200_OK)
async def ingest_document(
    body: IngestRequest,
    client_id: UUID = Depends(get_client_id_from_token),
) -> IngestResponse:
    """Ingest a complex document using Docling, then forward to process-document EF.

    1. Validate client_id matches authenticated user
    2. Download from Supabase Storage
    3. Parse with Docling (OCR, table extraction, layout analysis)
    4. Call process-document EF with pre_extracted_text
    5. Return result from EF
    """
    if str(client_id) != body.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="client_id in body does not match authenticated user.",
        )

    try:
        from blu_parsers.parsers.docling_parser import DoclingParser
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

        # 1. Download from Storage
        logger.info("Downloading %s for Docling parsing", body.storage_path)
        file_bytes = supabase.storage.from_("knowledge-base").download(body.storage_path)
        if not file_bytes:
            raise ValueError(f"Failed to download {body.storage_path}")

        # 2. Parse with Docling
        parser = DoclingParser()
        extracted_text = parser.parse(io.BytesIO(file_bytes))
        logger.info("Docling extracted %d chars from %s", len(extracted_text), body.file_name)

        if not extracted_text or not extracted_text.strip():
            raise ValueError("Docling extracted no text from document.")

        # 3. Forward to process-document EF with pre_extracted_text
        payload = {
            "document_id": body.document_id,
            "storage_path": body.storage_path,
            "client_id": body.client_id,
            "file_name": body.file_name,
            "file_type": body.file_type,
            "pre_extracted_text": extracted_text,
        }
        if body.target_tokens is not None:
            payload["target_tokens"] = body.target_tokens

        async with httpx.AsyncClient(timeout=300.0) as client:
            ef_response = await client.post(
                PROCESS_DOCUMENT_EF_URL,
                json=payload,
                headers={"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
            )

        if ef_response.status_code != 200:
            raise ValueError(
                f"process-document EF returned {ef_response.status_code}: {ef_response.text[:500]}"
            )

        ef_data = ef_response.json()
        return IngestResponse(
            document_id=body.document_id,
            status=ef_data.get("status", "completed"),
            message=ef_data.get("message", "Document ingested successfully."),
        )

    except Exception as exc:
        logger.error("ingest_document failed for %s: %s", body.document_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc.__class__.__name__}: {exc}",
        )
