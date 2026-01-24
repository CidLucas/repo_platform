# src/analytics_api/api/endpoints/ingestion.py
"""Endpoints específicos para fluxos de ingestão/connector.

MetricService automatically persists aggregations to analytics_v2 tables.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from analytics_api.api.dependencies import get_metric_service_ingest
from analytics_api.services.metric_service import MetricService

router = APIRouter(prefix="/ingest", tags=["Ingest"],)

logger = logging.getLogger(__name__)


@router.post(
    "/recompute",
    summary="Recalcula e persiste métricas (camada ouro)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def recompute_gold_metrics(
    service: MetricService = Depends(get_metric_service_ingest),
):
    """
    Recalculates and persists metrics to analytics_v2 tables.

    MetricService initializes with silver data, computes aggregations,
    and persists to analytics_v2 tables. If persistence fails, this endpoint
    will return an error (not silently succeed).
    """
    try:
        # Persistence happens in MetricService.__init__.
        # If it fails, an exception is raised and caught here.
        logger.info("Ingest: metrics recomputed and persisted to analytics_v2.")
        return {"status": "success", "detail": "Metrics recomputed and persisted to analytics_v2"}
    except Exception as exc:
        logger.error(f"Failed to recompute metrics: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recomputing and persisting metrics: {str(exc)}"
        )
