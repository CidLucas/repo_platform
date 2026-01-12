"""
API routes for connector status, sync history, and dashboard statistics.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from data_ingestion_api.schemas.connector_schemas import (
    ConnectorListResponse,
    SyncHistoryResponse,
    StartSyncRequest,
    StartSyncResponse,
    FileListResponse,
    DashboardStatsResponse,
)
from data_ingestion_api.services.connector_status_service import connector_status_service
from data_ingestion_api.services.file_metadata_service import file_metadata_service
from vizu_auth.fastapi.dependencies import create_auth_dependency

logger = logging.getLogger(__name__)

# Auth factory (JWT only via Supabase; API key disabled)
auth_factory = create_auth_dependency(api_key_lookup_fn=lambda _key: None)

router = APIRouter(
    prefix="/connectors",
    tags=["Connector Status & Metadata"]
)


# Derive the tenant/client id from the authenticated JWT to prevent caller spoofing
async def get_client_id_from_auth(auth=Depends(auth_factory.get_auth_result)) -> str:
    if not auth or not auth.client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="client_id missing from token")
    return str(auth.client_id)


@router.get(
    "/status",
    response_model=ConnectorListResponse,
    summary="Get all connectors with sync status for a client"
)
async def get_connector_status(
    client_id: str = Depends(get_client_id_from_auth),
    auth=Depends(auth_factory.get_auth_result),
):
    """
    Get all configured connectors for a client with latest sync status.

    Returns:
    - List of connectors with sync metadata
    - Total connected vs configured count
    """
    try:
        return await connector_status_service.get_connector_list(client_id)
    except Exception as e:
        logger.error(f"Failed to get connector status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve connector status: {str(e)}"
        )


@router.get(
    "/{credential_id}/sync-history",
    response_model=list[SyncHistoryResponse],
    summary="Get sync history for a specific connector"
)
async def get_sync_history(
    credential_id: int,
    limit: int = 10,
    auth=Depends(auth_factory.get_auth_result),
):
    """Get recent sync history for a connector."""
    try:
        return await connector_status_service.get_sync_history(credential_id, limit)
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sync history: {str(e)}"
        )


@router.post(
    "/sync/start",
    response_model=StartSyncResponse,
    summary="Start a new sync job"
)
async def start_sync_job(
    request: StartSyncRequest,
    auth=Depends(auth_factory.get_auth_result),
):
    """
    Start a new sync job for a connector.
    Creates a sync history record and triggers the ETL pipeline.
    """
    try:
        # Create sync record
        sync_id = await connector_status_service.create_sync_record(
            credential_id=request.credential_id,
            resource_type=request.resource_type,
        )

        # TODO: Trigger actual sync job (Pub/Sub, Cloud Tasks, etc.)
        # For now, just return the sync_id

        return StartSyncResponse(
            sync_id=sync_id,
            credential_id=request.credential_id,
            status="running",
            message=f"Sync job {sync_id} started successfully"
        )
    except Exception as e:
        logger.error(f"Failed to start sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync: {str(e)}"
        )


@router.get(
    "/files",
    response_model=FileListResponse,
    summary="Get uploaded files for a client"
)
async def get_uploaded_files(
    client_id: str,
    auth=Depends(auth_factory.get_auth_result),
):
    """Get all uploaded CSV/Excel files for a client."""
    try:
        return await file_metadata_service.get_uploaded_files(client_id)
    except Exception as e:
        logger.error(f"Failed to get uploaded files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve files: {str(e)}"
        )


@router.delete(
    "/files/{file_id}",
    summary="Delete an uploaded file"
)
async def delete_uploaded_file(
    file_id: UUID,
    client_id: str,
    auth=Depends(auth_factory.get_auth_result),
):
    """Delete a file (soft delete and remove from storage)."""
    try:
        await file_metadata_service.delete_file(file_id, client_id)
        return {"message": f"File {file_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get(
    "/dashboard-stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard statistics for admin home page"
)
async def get_dashboard_stats(
    client_id: str,
    auth=Depends(auth_factory.get_auth_result),
):
    """
    Get summary statistics for admin home page:
    - Total/connected/pending/error connectors
    - Storage usage (DB + files)
    - Last sync time
    - Syncs today
    """
    try:
        return await connector_status_service.get_dashboard_stats(client_id)
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )
