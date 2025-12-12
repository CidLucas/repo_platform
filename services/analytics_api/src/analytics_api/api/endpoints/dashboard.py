# src/analytics_api/api/endpoints/dashboard.py
from analytics_api.api.dependencies import get_metric_service
from fastapi import Depends, HTTPException, status
from vizu_auth.fastapi import create_auth_dependency
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.api.dependencies import get_postgres_repository
from pydantic import BaseModel

# IMPORTAÇÃO ATUALIZADA: Agora usa o schema específico da Home
from analytics_api.schemas.metrics import HomeMetricsResponse
from analytics_api.services.metric_service import MetricService
from fastapi import APIRouter, Depends

router = APIRouter()

# Dependência de autenticação (ajuste conforme sua factory real)
auth_dependency = create_auth_dependency(
    api_key_lookup_fn=lambda key: None,  # Substitua por função real se usar API Key
    external_user_lookup_fn=None,
)

class MeResponse(BaseModel):
    cliente_vizu_id: str

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

@router.get(
    "/me",
    response_model=MeResponse,
    summary="Retorna o cliente_vizu_id do usuário autenticado",
    tags=["Usuário"]
)
async def get_me(
    auth_result=Depends(auth_dependency.get_auth_result),
    repo: PostgresRepository = Depends(get_postgres_repository),
):
    """
    Retorna o cliente_vizu_id do usuário autenticado (cria se não existir).
    """
    # auth_result.external_user_id = user id do Supabase
    if not auth_result.external_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado.")
    cliente_vizu_id = repo.get_or_create_cliente_vizu_id(auth_result.external_user_id)
    return MeResponse(cliente_vizu_id=str(cliente_vizu_id))
