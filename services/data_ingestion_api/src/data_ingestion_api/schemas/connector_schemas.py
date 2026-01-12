"""
Pydantic schemas for connector status, sync history, and file metadata.
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from uuid import UUID


# --- Connector Status Schemas ---

class ConnectorStatusResponse(BaseModel):
    """Status of a single connector for a client."""

    credential_id: int
    nome_conexao: str
    tipo_servico: str  # 'BIGQUERY', 'SHOPIFY', etc.
    status: Literal['active', 'inactive', 'error', 'pending']

    # Latest sync information
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[Literal['completed', 'failed', 'running']] = None
    records_count: Optional[int] = None  # Total records from latest sync

    # Error information
    error_message: Optional[str] = None

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
    sync_completed_at: Optional[datetime] = None

    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0

    resource_type: Optional[str] = None
    error_message: Optional[str] = None

    created_at: datetime


class StartSyncRequest(BaseModel):
    """Request to start a new sync job."""

    credential_id: int = Field(..., description="ID of the credential to sync")
    resource_type: Optional[str] = Field(None, description="Specific resource to sync (products, orders, etc.)")


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
    file_type: Optional[str] = None

    status: Literal['uploaded', 'processing', 'completed', 'failed', 'deleted']
    records_count: int = 0
    records_imported: int = 0

    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    storage_path: str
    download_url: Optional[str] = None  # Signed URL for download


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
    quota_gb: Optional[float] = None
    usage_percentage: Optional[float] = None

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

    last_sync_at: Optional[datetime] = None
    total_syncs_today: int = 0
