"""
Service for managing connector status, sync history, and metadata.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from data_ingestion_api.services import supabase_client
from data_ingestion_api.schemas.connector_schemas import (
    ConnectorStatusResponse,
    ConnectorListResponse,
    SyncHistoryResponse,
    StorageUsageResponse,
    DashboardStatsResponse,
)

logger = logging.getLogger(__name__)


class ConnectorStatusService:
    """Service for connector status and metadata operations."""

    async def get_connector_list(self, client_id: str) -> ConnectorListResponse:
        """
        Get all connectors for a client with their latest sync status.

        Joins:
        - credencial_servico_externo
        - connector_sync_history (latest record per credential)
        """
        # 1. Get all credentials for this client
        credentials = await supabase_client.select(
            table="credencial_servico_externo",
            columns="*",
            filters={"client_id": client_id},
            client_id=client_id,
        )

        connectors = []
        connected_count = 0

        # 2. For each credential, get latest sync history
        for cred in credentials:
            # Get latest completed sync
            latest_sync = await self._get_latest_sync(cred["id"])

            status = cred.get("status", "pending")
            if status == "active":
                connected_count += 1

            connector = ConnectorStatusResponse(
                credential_id=cred["id"],
                nome_conexao=cred["nome_servico"],
                tipo_servico=cred.get("tipo_servico", "UNKNOWN"),
                status=status,
                last_sync_at=latest_sync.get("sync_completed_at") if latest_sync else None,
                last_sync_status=latest_sync.get("status") if latest_sync else None,
                records_count=latest_sync.get("records_inserted", 0) if latest_sync else None,
                error_message=latest_sync.get("error_message") if latest_sync else None,
                created_at=cred.get("created_at", datetime.utcnow()),
                updated_at=cred.get("updated_at", datetime.utcnow()),
            )
            connectors.append(connector)

        return ConnectorListResponse(
            connectors=connectors,
            total_connected=connected_count,
            total_configured=len(connectors),
        )

    async def _get_latest_sync(self, credential_id: int) -> Optional[dict]:
        """Get the latest sync history record for a credential."""
        syncs = await supabase_client.select(
            table="connector_sync_history",
            columns="*",
            filters={"credential_id": credential_id},
        )

        if not syncs:
            return None

        # Sort by completed_at descending, then started_at
        syncs.sort(
            key=lambda x: (
                x.get("sync_completed_at") or datetime.min.isoformat(),
                x.get("sync_started_at") or datetime.min.isoformat()
            ),
            reverse=True
        )

        return syncs[0]

    async def get_sync_history(
        self,
        credential_id: int,
        limit: int = 10
    ) -> list[SyncHistoryResponse]:
        """Get sync history for a specific credential."""
        syncs = await supabase_client.select(
            table="connector_sync_history",
            columns="*",
            filters={"credential_id": credential_id},
        )

        # Sort and limit
        syncs.sort(key=lambda x: x.get("sync_started_at", datetime.min.isoformat()), reverse=True)
        syncs = syncs[:limit]

        return [SyncHistoryResponse(**sync) for sync in syncs]

    async def create_sync_record(
        self,
        credential_id: int,
        resource_type: Optional[str] = None,
    ) -> UUID:
        """
        Create a new sync history record (status: running).
        Returns the sync_id for tracking.
        """
        data = {
            "credential_id": credential_id,
            "status": "running",
            "sync_started_at": datetime.utcnow().isoformat(),
            "resource_type": resource_type,
        }

        result = await supabase_client.insert("connector_sync_history", data)
        return UUID(result["id"])

    async def update_sync_record(
        self,
        sync_id: UUID,
        status: str,
        records_processed: Optional[int] = None,
        records_inserted: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update sync history record with completion status."""
        data = {
            "status": status,
            "sync_completed_at": datetime.utcnow().isoformat(),
        }

        if records_processed is not None:
            data["records_processed"] = records_processed
        if records_inserted is not None:
            data["records_inserted"] = records_inserted
        if error_message:
            data["error_message"] = error_message

        await supabase_client.update(
            table="connector_sync_history",
            data=data,
            filters={"id": str(sync_id)},
        )

    async def get_storage_usage(self, client_id: str) -> StorageUsageResponse:
        """
        Calculate storage usage for a client.

        Combines:
        1. Database size (analytics_silver table filtered by client_id)
        2. File storage (uploaded_files_metadata)

        Note: Returns zero values if tables don't exist yet (they will be created in Phase 1).
        """
        # 1. Get file storage from uploaded_files_metadata
        # NOTE: Table may not exist yet - handle gracefully
        try:
            files = await supabase_client.select(
                table="uploaded_files_metadata",
                columns="file_size_bytes",
                filters={"client_id": client_id, "status": "completed"},
                client_id=client_id,
            )
            file_storage_bytes = sum(f.get("file_size_bytes", 0) for f in files)
        except Exception as e:
            logger.debug(f"uploaded_files_metadata table not found or empty: {e}")
            files = []
            file_storage_bytes = 0

        # 2. Estimate database size (analytics_silver records)
        # Note: This is an approximation. For exact size, use pg_total_relation_size
        try:
            records = await supabase_client.select(
                table="analytics_silver",
                columns="id",  # Just count
                filters={"client_id": client_id},
                client_id=client_id,
            )
        except Exception as e:
            logger.debug(f"analytics_silver table not found or empty: {e}")
            records = []

        # Estimate: ~1KB per record (conservative estimate)
        estimated_db_bytes = len(records) * 1024

        total_bytes = file_storage_bytes + estimated_db_bytes

        return StorageUsageResponse(
            database_size_bytes=estimated_db_bytes,
            database_size_mb=estimated_db_bytes / (1024 * 1024),
            file_storage_bytes=file_storage_bytes,
            file_storage_mb=file_storage_bytes / (1024 * 1024),
            total_storage_bytes=total_bytes,
            total_storage_mb=total_bytes / (1024 * 1024),
            total_storage_gb=total_bytes / (1024 * 1024 * 1024),
            quota_gb=2000,  # Default 2TB quota
            usage_percentage=(total_bytes / (2000 * 1024 * 1024 * 1024)) * 100 if total_bytes > 0 else 0,
            total_files=len(files),
            total_records=len(records),
        )

    async def get_dashboard_stats(self, client_id: str) -> DashboardStatsResponse:
        """Get summary statistics for admin home page."""
        # Get connector list
        connector_list = await self.get_connector_list(client_id)

        # Get storage usage
        storage = await self.get_storage_usage(client_id)

        # Count connectors by status
        error_count = sum(1 for c in connector_list.connectors if c.status == 'error')
        pending_count = sum(1 for c in connector_list.connectors if c.status == 'pending')

        # Get latest sync time
        latest_sync = None
        for connector in connector_list.connectors:
            if connector.last_sync_at:
                if latest_sync is None or connector.last_sync_at > latest_sync:
                    latest_sync = connector.last_sync_at

        # Count syncs today
        today = datetime.utcnow().date()
        all_syncs = await supabase_client.select(
            table="connector_sync_history",
            columns="sync_started_at",
        )
        syncs_today = sum(
            1 for s in all_syncs
            if datetime.fromisoformat(s["sync_started_at"].replace("Z", "+00:00")).date() == today
        )

        return DashboardStatsResponse(
            total_connectors=connector_list.total_configured,
            connected_connectors=connector_list.total_connected,
            pending_connectors=pending_count,
            error_connectors=error_count,
            storage_usage=storage,
            last_sync_at=latest_sync,
            total_syncs_today=syncs_today,
        )


# Singleton instance
connector_status_service = ConnectorStatusService()
