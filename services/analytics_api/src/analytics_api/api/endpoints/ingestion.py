# src/analytics_api/api/endpoints/ingestion.py
"""Endpoints específicos para fluxos de ingestão/connector.

Estes endpoints instanciam o MetricService com write_gold=True,
recomputam agregações e persistem na camada ouro.
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
    Usa o MetricService em modo write_gold=True para recalcular agregações
    a partir da camada prata e persistir nas tabelas ouro.

    Destinado ao modal de connector (ingestão). Requer client_id via
    query/header/JWT conforme get_client_id.
    """
    try:
        # A persistência acontece no __init__ quando write_gold=True.
        logger.info("Ingest: métricas recalculadas e persistidas na camada ouro.")
        return {"status": "accepted", "detail": "Gold metrics recomputed"}
    except Exception as exc:  # defensive: should already be covered in dependency
        logger.error(f"Falha ao recalcular métricas ouro: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao recalcular métricas ouro"
        )
