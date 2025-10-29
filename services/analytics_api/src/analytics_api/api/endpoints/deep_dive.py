# services/analytics_api/src/analytics_api/api/endpoints/deep_dive.py
from fastapi import APIRouter, Depends, HTTPException, Path
from analytics_api.services.metric_service import MetricService
from analytics_api.api.dependencies import get_metric_service
# IMPORTAÇÕES ATUALIZADAS: Schemas específicos para cada detalhe
from analytics_api.schemas.metrics import (
    FornecedorDetailResponse,
    ClienteDetailResponse,
    ProdutoDetailResponse,
    PedidoDetailResponse
)

router = APIRouter()

# --- Endpoint para Detalhe FORNECEDOR ---
@router.get(
    "/fornecedor/{nome_fornecedor}",
    response_model=FornecedorDetailResponse,
    summary="Detalhe do Fornecedor (Nível 3)",
    tags=["Nível 3 - Detalhe"]
)
def get_fornecedor_detail_endpoint(
    # Validação do Path Parameter
    nome_fornecedor: str = Path(..., description="Nome do fornecedor (emitter_nome), URL-encoded"),
    service: MetricService = Depends(get_metric_service)
):
    """Retorna dados cadastrais e rankings internos para um Fornecedor."""
    try:
        # CHAMA A NOVA FUNÇÃO DO SERVICE
        return service.get_fornecedor_details(nome_fornecedor=nome_fornecedor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Endpoint para Detalhe CLIENTE ---
@router.get(
    "/cliente/{nome_cliente}",
    response_model=ClienteDetailResponse,
    summary="Detalhe do Cliente (Nível 3)",
    tags=["Nível 3 - Detalhe"]
)
def get_cliente_detail_endpoint(
    nome_cliente: str = Path(..., description="Nome do cliente (receiver_nome), URL-encoded"),
    service: MetricService = Depends(get_metric_service)
):
    """Retorna dados cadastrais, scorecards e rankings internos para um Cliente."""
    try:
        # CHAMA A NOVA FUNÇÃO DO SERVICE
        return service.get_cliente_details(nome_cliente=nome_cliente)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Endpoint para Detalhe PRODUTO ---
@router.get(
    "/produto/{nome_produto}",
    response_model=ProdutoDetailResponse,
    summary="Detalhe do Produto (Nível 3)",
    tags=["Nível 3 - Detalhe"]
)
def get_produto_detail_endpoint(
    nome_produto: str = Path(..., description="Nome do produto (raw_product_description), URL-encoded"),
    service: MetricService = Depends(get_metric_service)
):
    """Retorna scorecards, gráficos e rankings internos para um Produto."""
    try:
        # CHAMA A NOVA FUNÇÃO DO SERVICE
        return service.get_produto_details(nome_produto=nome_produto)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Endpoint para Detalhe PEDIDO ---
@router.get(
    "/pedido/{order_id}",
    response_model=PedidoDetailResponse,
    summary="Detalhe do Pedido (Nível 3)",
    tags=["Nível 3 - Detalhe"]
)
def get_pedido_detail_endpoint(
    order_id: str = Path(..., description="ID único do pedido (order_id)"),
    service: MetricService = Depends(get_metric_service)
):
    """Retorna os dados do cliente e os itens de linha para um Pedido."""
    try:
        # CHAMA A NOVA FUNÇÃO DO SERVICE
        return service.get_pedido_details(order_id=order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))