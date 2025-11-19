# services/analytics_api/src/analytics_api/api/endpoints/rankings.py
from fastapi import APIRouter, Depends, HTTPException
from analytics_api.services.metric_service import MetricService
from analytics_api.api.dependencies import get_metric_service
# IMPORTAÇÕES ATUALIZADAS: Schemas específicos para cada módulo
from analytics_api.schemas.metrics import (
    FornecedoresOverviewResponse,
    ClientesOverviewResponse,
    ProdutosOverviewResponse,
    PedidosOverviewResponse
)

router = APIRouter()

# --- Endpoint para Módulo FORNECEDORES ---
@router.get(
    "/fornecedores",
    response_model=FornecedoresOverviewResponse,
    summary="Visão Geral Fornecedores (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_fornecedores_overview_endpoint(
    service: MetricService = Depends(get_metric_service)
):
    """Retorna KPIs, rankings e gráficos para a página de Fornecedores."""
    # CHAMA A NOVA FUNÇÃO DO SERVICE
    return service.get_fornecedores_overview()

# --- Endpoint para Módulo CLIENTES ---
@router.get(
    "/clientes",
    response_model=ClientesOverviewResponse,
    summary="Visão Geral Clientes (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_clientes_overview_endpoint(
    service: MetricService = Depends(get_metric_service)
):
    """Retorna KPIs, rankings e gráficos para a página de Clientes."""
    # CHAMA A NOVA FUNÇÃO DO SERVICE
    return service.get_clientes_overview()

# --- Endpoint para Módulo PRODUTOS ---
@router.get(
    "/produtos",
    response_model=ProdutosOverviewResponse,
    summary="Visão Geral Produtos (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_produtos_overview_endpoint(
    service: MetricService = Depends(get_metric_service)
):
    """Retorna KPIs e rankings para a página de Produtos."""
    # CHAMA A NOVA FUNÇÃO DO SERVICE
    return service.get_produtos_overview()

# --- Endpoint para Módulo PEDIDOS ---
@router.get(
    "/pedidos",
    response_model=PedidosOverviewResponse,
    summary="Visão Geral Pedidos (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_pedidos_overview_endpoint(
    service: MetricService = Depends(get_metric_service)
):
    """Retorna KPIs e lista de últimos pedidos para a página de Pedidos."""
    # CHAMA A NOVA FUNÇÃO DO SERVICE
    return service.get_pedidos_overview()