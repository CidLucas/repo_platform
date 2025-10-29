# src/analytics_api/api/endpoints/dashboard.py
from fastapi import APIRouter, Depends
from analytics_api.services.metric_service import MetricService
from analytics_api.api.dependencies import get_metric_service
# IMPORTAÇÃO ATUALIZADA: Agora usa o schema específico da Home
from analytics_api.schemas.metrics import HomeMetricsResponse

router = APIRouter()

@router.get(
    "/home",
    # RESPONSE_MODEL ATUALIZADO: Corresponde ao schema novo
    response_model=HomeMetricsResponse,
    summary="Métricas Agregadas (Nível 1)",
    tags=["Nível 1 - Home"]
)
def get_home_dashboard(
    service: MetricService = Depends(get_metric_service)
):
    """
    Retorna os scorecards agregados e gráficos para a página
    principal (Home) do cliente.
    """
    # Nenhuma mudança aqui, a função já era get_home_metrics
    metrics_data = service.get_home_metrics()
    return metrics_data