# src/analytics_api/api/endpoints/ingestion.py
"""Endpoints específicos para fluxos de ingestão/connector.

MetricService automatically persists aggregations to analytics_v2 tables.
Supports incremental mode for daily updates (only fetches new data since last sync).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from analytics_api.api.dependencies import get_postgres_repository, get_client_id
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.metric_service import MetricService

router = APIRouter(prefix="/ingest", tags=["Ingest"],)

logger = logging.getLogger(__name__)


@router.post(
    "/recompute",
    summary="Recalcula e persiste métricas (camada ouro)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def recompute_gold_metrics(
    force_full: bool = Query(
        default=False,
        description="Force full reload even if previous sync exists. Default: auto-detect."
    ),
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Recalculates and persists metrics to analytics_v2 tables.

    Mode is AUTO-DETECTED:
    - If this is the first sync (no last_synced_at), does a FULL load
    - If previous sync exists, does an INCREMENTAL load (only new data)
    - Use force_full=true to override and force a full reload

    MetricService initializes with silver data, computes aggregations,
    and persists to analytics_v2 tables. If persistence fails, this endpoint
    will return an error (not silently succeed).
    """
    try:
        # Auto-detect mode: check if previous sync exists AND there's actual data
        last_sync = repo.get_last_sync_timestamp(client_id)

        # Even if we have a last_sync timestamp, check if there's actually data
        # in analytics_v2. If no data exists, we need a full load regardless.
        has_existing_data = False
        if last_sync is not None:
            has_existing_data = repo.has_analytics_data(client_id)
            if not has_existing_data:
                logger.warning(
                    f"last_sync exists ({last_sync}) but no analytics_v2 data found - forcing full load"
                )

        if force_full:
            incremental = False
            mode_str = "full (forced)"
        elif last_sync is not None and has_existing_data:
            incremental = True
            mode_str = f"incremental (since {last_sync})"
        else:
            incremental = False
            mode_str = "full (first sync)" if last_sync is None else "full (no data found)"

        logger.info(f"Starting {mode_str} recompute for client {client_id}")

        # Initialize MetricService with auto-detected incremental flag
        # Persistence happens in MetricService.__init__
        service = MetricService(repository=repo, client_id=client_id, incremental=incremental)

        rows_processed = len(service.df) if service.df is not None else 0
        logger.info(f"Ingest: {mode_str} recompute completed for {client_id} ({rows_processed} rows)")

        return {
            "status": "success",
            "mode": "incremental" if incremental else "full",
            "auto_detected": not force_full,
            "last_sync": str(last_sync) if last_sync else None,
            "rows_processed": rows_processed,
            "detail": f"Metrics recomputed ({mode_str}) and persisted to analytics_v2"
        }
    except Exception as exc:
        logger.error(f"Failed to recompute metrics: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recomputing and persisting metrics: {str(exc)}"
        )


@router.post(
    "/recompute/full",
    summary="Force full reload - ignores last sync timestamp",
    status_code=status.HTTP_202_ACCEPTED,
)
async def recompute_full(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Force a full reload from source, ignoring any previous sync.
    Equivalent to calling /recompute?force_full=true

    Use this when you need to re-sync all historical data.
    """
    try:
        logger.info(f"Starting FULL recompute for client {client_id} (forced)")

        # Initialize MetricService with incremental=False (full reload)
        service = MetricService(repository=repo, client_id=client_id, incremental=False)

        rows_processed = len(service.df) if service.df is not None else 0
        logger.info(f"Ingest: full recompute completed for {client_id} ({rows_processed} rows)")

        return {
            "status": "success",
            "mode": "full",
            "rows_processed": rows_processed,
            "detail": "Full reload completed and persisted to analytics_v2"
        }
    except Exception as exc:
        logger.error(f"Failed to run full recompute: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in full recompute: {str(exc)}"
        )
