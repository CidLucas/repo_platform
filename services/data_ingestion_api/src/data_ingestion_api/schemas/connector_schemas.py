"""
Pydantic schemas for connector status, sync history, and file metadata.
"""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# --- Connector Status Schemas ---

class ConnectorStatusResponse(BaseModel):
    """Status of a single connector for a client."""

    credential_id: int
    nome_conexao: str
    tipo_servico: str  # 'BIGQUERY', 'SHOPIFY', etc.
    status: Literal['active', 'inactive', 'error', 'pending']

    # Latest sync information
    last_sync_at: datetime | None = None
    last_sync_status: Literal['completed', 'failed', 'running'] | None = None
    records_count: int | None = None  # Total records from latest sync

    # Error information
    error_message: str | None = None

    created_at: datetime
    updated_at: datetime


class ConnectorListResponse(BaseModel):
    """List of all connectors for a client."""

    connectors: list[ConnectorStatusResponse]
    total_connected: int
    total_configured: int


# --- Sync History Schemas ---

class SyncHistoryResponse(BaseModel):
    """Single sync history record."""

    id: UUID
    credential_id: int
    status: Literal['running', 'completed', 'failed', 'cancelled']

    sync_started_at: datetime
    sync_completed_at: datetime | None = None

    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0

    resource_type: str | None = None
    error_message: str | None = None

    created_at: datetime


class StartSyncRequest(BaseModel):
    """Request to start a new sync job."""

    credential_id: int = Field(..., description="ID of the credential to sync")
    resource_type: str | None = Field(None, description="Specific resource to sync (products, orders, etc.)")


class StartSyncResponse(BaseModel):
    """Response when starting a sync job."""

    sync_id: UUID
    credential_id: int
    status: str
    message: str


# --- File Upload Schemas ---

class UploadedFileResponse(BaseModel):
    """Metadata for an uploaded file."""

    id: UUID
    file_name: str
    file_size_bytes: int
    file_type: str | None = None

    status: Literal['uploaded', 'processing', 'completed', 'failed', 'deleted']
    records_count: int = 0
    records_imported: int = 0

    uploaded_at: datetime
    processed_at: datetime | None = None

    storage_path: str
    download_url: str | None = None  # Signed URL for download


class FileListResponse(BaseModel):
    """List of uploaded files for a client."""

    files: list[UploadedFileResponse]
    total_files: int
    total_size_bytes: int


# --- Usage Statistics Schemas ---

class StorageUsageResponse(BaseModel):
    """Storage usage statistics for a client."""

    # Database storage
    database_size_bytes: int
    database_size_mb: float

    # File storage (Supabase Storage)
    file_storage_bytes: int
    file_storage_mb: float

    # Combined
    total_storage_bytes: int
    total_storage_mb: float
    total_storage_gb: float

    # Quota (if applicable)
    quota_gb: float | None = None
    usage_percentage: float | None = None

    # File counts
    total_files: int
    total_records: int


class DashboardStatsResponse(BaseModel):
    """Summary statistics for admin home page."""

    total_connectors: int
    connected_connectors: int
    pending_connectors: int
    error_connectors: int

    storage_usage: StorageUsageResponse

    last_sync_at: datetime | None = None
    total_syncs_today: int = 0
