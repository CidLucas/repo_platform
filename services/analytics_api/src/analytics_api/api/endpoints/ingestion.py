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

        # 🔄 REFRESH MATERIALIZED VIEWS after data is written
        # This ensures MVs reflect the latest data in fact_sales
        logger.info(f"📊 Refreshing materialized views to reflect new data...")
        mv_result = repo.refresh_materialized_views()

        return {
            "status": "success",
            "mode": "incremental" if incremental else "full",
            "auto_detected": not force_full,
            "last_sync": str(last_sync) if last_sync else None,
            "rows_processed": rows_processed,
            "detail": f"Metrics recomputed ({mode_str}) and persisted to analytics_v2",
            "materialized_views_refreshed": mv_result.get("status") == "success",
            "materialized_views": mv_result.get("views_refreshed", {})
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

        # 🔄 REFRESH MATERIALIZED VIEWS after data is written
        logger.info(f"📊 Refreshing materialized views to reflect new data...")
        mv_result = repo.refresh_materialized_views()

        return {
            "status": "success",
            "mode": "full",
            "rows_processed": rows_processed,
            "detail": "Full reload completed and persisted to analytics_v2",
            "materialized_views_refreshed": mv_result.get("status") == "success",
            "materialized_views": mv_result.get("views_refreshed", {})
        }
    except Exception as exc:
        logger.error(f"Failed to run full recompute: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in full recompute: {str(exc)}"
        )


@router.post(
    "/refresh-views",
    summary="Refresh materialized views (admin endpoint)",
    status_code=status.HTTP_200_OK,
)
async def refresh_materialized_views(
    repo: PostgresRepository = Depends(get_postgres_repository),
):
    """
    Manually refresh all materialized views in analytics_v2 schema.

    This endpoint refreshes:
    - mv_customer_summary
    - mv_product_summary
    - mv_monthly_sales_trend

    **Use Cases:**
    - Manual refresh between scheduled ingestions
    - Testing after manual data modifications
    - Part of scheduled jobs (e.g., hourly refresh)

    **Scope**: Global (refreshes for ALL clients)

    Returns:
        Refresh status for each view
    """
    try:
        logger.info("🔄 Admin: Refreshing all materialized views")
        result = repo.refresh_materialized_views()

        if result.get("status") == "success":
            return {
                "status": "success",
                "detail": "All materialized views refreshed successfully",
                "elapsed_seconds": result.get("elapsed_seconds"),
                "views": result.get("views_refreshed", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to refresh views: {result.get('error')}"
            )

    except Exception as exc:
        logger.error(f"Failed to refresh materialized views: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing materialized views: {str(exc)}"
        )
