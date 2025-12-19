# src/analytics_api/api/endpoints/dashboard.py
from analytics_api.api.dependencies import (
    get_metric_service,
    get_postgres_repository,
)
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.schemas.metrics import HomeMetricsResponse
from analytics_api.services.metric_service import MetricService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from vizu_auth.fastapi import create_auth_dependency

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
    tags=["Nível 1 - Home"],
)
def get_home_dashboard(service: MetricService = Depends(get_metric_service)):
    """
    Retorna os scorecards agregados e gráficos para a página
    principal (Home) do cliente.
    """
    # Nenhuma mudança aqui, a função já era get_home_metrics
    metrics_data = service.get_home_metrics()
    return metrics_data


@router.get(
    "/home_gold",
    response_model=HomeMetricsResponse,
    summary="Métricas Agregadas (Nível 1) - View Ouro",
    tags=["Nível 1 - Home", "Ouro"],
)
def get_home_dashboard_gold(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna os scorecards agregados e gráficos para a página principal (Home) do cliente,
    consultando a view ouro (analytics_gold_orders).
    """
    metrics_data = repo.get_gold_orders_metrics()
    return metrics_data


@router.get(
    "/produtos/gold",
    summary="Métricas agregadas de produtos - View Ouro",
    tags=["Produtos", "Ouro"],
)
def get_products_gold(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna métricas agregadas de produtos a partir da view ouro (analytics_gold_products).
    """
    return repo.get_gold_products_metrics()


@router.get(
    "/clientes/gold",
    summary="Métricas agregadas de clientes - View Ouro",
    tags=["Clientes", "Ouro"],
)
def get_customers_gold(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna métricas agregadas de clientes a partir da view ouro (analytics_gold_customers).
    """
    return repo.get_gold_customers_metrics()


@router.get(
    "/fornecedores/gold",
    summary="Métricas agregadas de fornecedores - View Ouro",
    tags=["Fornecedores", "Ouro"],
)
def get_suppliers_gold(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna métricas agregadas de fornecedores a partir da view ouro (analytics_gold_suppliers).
    """
    return repo.get_gold_suppliers_metrics()


@router.get(
    "/fornecedores",
    summary="Métricas agregadas de fornecedores",
    tags=["Fornecedores"],
)
def get_suppliers(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna métricas agregadas de fornecedores a partir da view ouro (analytics_gold_suppliers).
    """
    return repo.get_gold_suppliers_metrics()

@router.get(
    "/produtos",
    summary="Métricas agregadas de produtos",
    tags=["Produtos"],
)
def get_products(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna métricas agregadas de produtos a partir da view ouro (analytics_gold_products).
    """
    return repo.get_gold_products_metrics()

@router.get(
    "/clientes",
    summary="Métricas agregadas de clientes",
    tags=["Clientes"],
)
def get_customers(repo: PostgresRepository = Depends(get_postgres_repository)):
    """
    Retorna métricas agregadas de clientes a partir da view ouro (analytics_gold_customers).
    """
    return repo.get_gold_customers_metrics()


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Retorna o cliente_vizu_id do usuário autenticado",
    tags=["Usuário"],
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado."
        )
    cliente_vizu_id = repo.get_or_create_cliente_vizu_id(auth_result.external_user_id)
    return MeResponse(cliente_vizu_id=str(cliente_vizu_id))
