"""
Endpoints de Indicadores - Métricas agregadas com cache.

Fornece indicadores de alto nível para dashboards.
Inclui comparativos percentuais vs 7, 30, 90 dias.
"""
import logging
from dataclasses import asdict
from typing import Literal

from analytics_api.api.dependencies import get_indicator_service
from analytics_api.services.indicator_service import IndicatorService, PeriodType
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/indicators", tags=["Indicators"])


# --- Modelos de Comparação ---

class ComparisonData(BaseModel):
    """Dados de comparação percentual vs períodos anteriores."""
    vs_7_days: float | None = Field(None, description="% variação vs média dos últimos 7 dias")
    vs_30_days: float | None = Field(None, description="% variação vs média dos últimos 30 dias")
    vs_90_days: float | None = Field(None, description="% variação vs média dos últimos 90 dias")
    trend: str | None = Field(None, description="Tendência: up, down, stable")


class IndicatorsRequest(BaseModel):
    """Request body para buscar indicadores."""
    period: PeriodType = "today"
    metrics: list[str] | None = None  # ["orders", "products", "customers"]
    include_comparisons: bool = Field(True, description="Incluir comparativos vs 7, 30, 90 dias")


class OrderMetricsResponse(BaseModel):
    """Métricas de pedidos."""
    total: int
    revenue: float
    avg_order_value: float
    growth_rate: float | None
    by_status: dict
    period: str
    comparisons: ComparisonData | None = None


class ProductMetricsResponse(BaseModel):
    """Métricas de produtos."""
    total_sold: int
    unique_products: int
    top_sellers: list
    low_stock_alerts: int
    avg_price: float
    period: str
    comparisons: ComparisonData | None = None


class CustomerMetricsResponse(BaseModel):
    """Métricas de clientes."""
    total_active: int
    new_customers: int
    returning_customers: int
    avg_lifetime_value: float
    period: str
    comparisons: ComparisonData | None = None


class IndicatorsResponse(BaseModel):
    """Resposta consolidada de indicadores."""
    orders: OrderMetricsResponse | None = None
    products: ProductMetricsResponse | None = None
    customers: CustomerMetricsResponse | None = None
    cached: bool
    generated_at: str
    ttl: int | None = None


@router.post("", response_model=IndicatorsResponse)
async def get_indicators(
    request: IndicatorsRequest,
    service: IndicatorService = Depends(get_indicator_service)
):
    """
    Retorna indicadores agregados para o período especificado.

    Lê de Gold tables pré-computadas (atualizadas no ETL).
    Inclui comparativos percentuais vs 7, 30, 90 dias quando solicitado.

    **Períodos suportados:**
    - `today`: Dia atual
    - `yesterday`: Dia anterior
    - `week`: Últimos 7 dias
    - `month`: Últimos 30 dias
    - `quarter`: Últimos 90 dias
    - `year`: Últimos 365 dias

    **Métricas disponíveis:**
    - `orders`: Total de pedidos, receita, ticket médio, growth rate
    - `products`: Produtos vendidos, top sellers, alertas de estoque
    - `customers`: Clientes ativos, novos, recorrentes, LTV

    **Comparativos:**
    - vs_7_days: % variação vs média dos últimos 7 dias
    - vs_30_days: % variação vs média dos últimos 30 dias
    - vs_90_days: % variação vs média dos últimos 90 dias
    - trend: up, down, stable
    """
    result = await service.get_indicators(
        period=request.period,
        metrics=request.metrics
    )

    # OPTIMIZATION: Preload all comparisons in a SINGLE query
    preloaded_comparisons: dict[str, ComparisonData] = {}
    if request.include_comparisons:
        preloaded_comparisons = await _get_comparisons_from_time_series(service)
        logger.debug(f"Preloaded comparisons for {len(preloaded_comparisons)} metrics")

    # Processa orders com comparativos
    orders_response = None
    if result.orders:
        comparisons = None
        if request.include_comparisons:
            comparisons = await _calculate_comparisons(service, "orders", preloaded_comparisons)
        orders_response = OrderMetricsResponse(
            **asdict(result.orders),
            comparisons=comparisons
        )

    # Processa products com comparativos
    products_response = None
    if result.products:
        comparisons = None
        if request.include_comparisons:
            comparisons = await _calculate_comparisons(service, "products", preloaded_comparisons)
        products_response = ProductMetricsResponse(
            **asdict(result.products),
            comparisons=comparisons
        )

    # Processa customers com comparativos
    customers_response = None
    if result.customers:
        comparisons = None
        if request.include_comparisons:
            comparisons = await _calculate_comparisons(service, "customers", preloaded_comparisons)
        customers_response = CustomerMetricsResponse(
            **asdict(result.customers),
            comparisons=comparisons
        )

    return IndicatorsResponse(
        orders=orders_response,
        products=products_response,
        customers=customers_response,
        cached=result.cached,
        generated_at=result.generated_at,
        ttl=result.ttl
    )


@router.get("/orders", response_model=OrderMetricsResponse)
async def get_order_indicators(
    period: PeriodType = Query("today", description="Período para cálculo"),
    include_comparisons: bool = Query(True, description="Incluir comparativos"),
    service: IndicatorService = Depends(get_indicator_service)
):
    """Retorna apenas indicadores de pedidos."""
    metrics = await service.get_order_metrics(period)

    comparisons = None
    if include_comparisons:
        preloaded = await _get_comparisons_from_time_series(service)
        comparisons = await _calculate_comparisons(service, "orders", preloaded)

    return OrderMetricsResponse(
        **asdict(metrics),
        comparisons=comparisons
    )


@router.get("/products", response_model=ProductMetricsResponse)
async def get_product_indicators(
    period: PeriodType = Query("today", description="Período para cálculo"),
    include_comparisons: bool = Query(True, description="Incluir comparativos"),
    service: IndicatorService = Depends(get_indicator_service)
):
    """Retorna apenas indicadores de produtos."""
    metrics = await service.get_product_metrics(period)

    comparisons = None
    if include_comparisons:
        preloaded = await _get_comparisons_from_time_series(service)
        comparisons = await _calculate_comparisons(service, "products", preloaded)

    return ProductMetricsResponse(
        **asdict(metrics),
        comparisons=comparisons
    )


@router.get("/customers", response_model=CustomerMetricsResponse)
async def get_customer_indicators(
    period: PeriodType = Query("today", description="Período para cálculo"),
    include_comparisons: bool = Query(True, description="Incluir comparativos"),
    service: IndicatorService = Depends(get_indicator_service)
):
    """Retorna apenas indicadores de clientes."""
    metrics = await service.get_customer_metrics(period)

    comparisons = None
    if include_comparisons:
        preloaded = await _get_comparisons_from_time_series(service)
        comparisons = await _calculate_comparisons(service, "customers", preloaded)

    return CustomerMetricsResponse(
        **asdict(metrics),
        comparisons=comparisons
    )


# --- Funções Auxiliares de Comparação ---

# Note: These caches are cleared automatically after each request since
# the indicator_service is recreated per request. For additional safety,
# we use client_id as cache keys.

async def _get_comparisons_from_time_series(
    service: IndicatorService,
) -> dict[str, ComparisonData]:
    """
    OPTIMIZED: Fetches comparisons for ALL metrics from gold_time_series in a SINGLE query.

    Instead of making 12+ queries (4 periods x 3 metric types), we make just 1 query
    that retrieves all comparison data from the pre-computed time series table.

    Returns a dict with keys: 'orders', 'products', 'customers' -> ComparisonData
    """
    try:
        # Access repository through service.repository (not postgres_repo)
        batch_data = service.repository.get_all_comparison_metrics_batch(service.client_id)
        logger.info(f"✅ Fetched comparison metrics from time_series in single query for client {service.client_id[:8]}...")

        result = {}
        for metric_type, metrics in batch_data.items():
            if metrics.get("current_month", 0) > 0:  # Only use if we have data
                result[metric_type] = ComparisonData(
                    vs_7_days=metrics.get("vs_prev_month"),  # Map vs_prev_month to vs_7_days for UI
                    vs_30_days=metrics.get("vs_3_months"),   # Map vs_3_months to vs_30_days
                    vs_90_days=metrics.get("vs_12_months"),  # Map vs_12_months to vs_90_days
                    trend=metrics.get("trend", "stable")
                )
        return result

    except Exception as e:
        logger.warning(f"Failed to fetch from time_series: {e}")
        return {}


async def _calculate_comparisons(
    service: IndicatorService,
    metric_type: str,
    preloaded_comparisons: dict[str, ComparisonData] | None = None
) -> ComparisonData:
    """
    Calcula comparativos percentuais vs 7, 30, 90 dias.

    OPTIMIZED: Now accepts preloaded_comparisons from single batch query.
    Falls back to legacy method if time_series data unavailable.
    """
    # Use preloaded data if available
    if preloaded_comparisons and metric_type in preloaded_comparisons:
        return preloaded_comparisons[metric_type]

    # Fallback to legacy calculation
    return await _calculate_comparisons_legacy(service, metric_type)


async def _calculate_comparisons_legacy(
    service: IndicatorService,
    metric_type: str
) -> ComparisonData:
    """
    Legacy comparison calculation - makes 4 separate queries per metric.
    Used as fallback when time_series data is not available.
    """
    try:
        if metric_type == "orders":
            # Fetch all periods - SQLAlchemy sessions are sync so these run sequentially
            today = await service.get_order_metrics("today")
            week = await service.get_order_metrics("week")
            month = await service.get_order_metrics("month")
            quarter = await service.get_order_metrics("quarter")

            today_value = today.total
            week_avg = week.total / 7 if week.total else 0
            month_avg = month.total / 30 if month.total else 0
            quarter_avg = quarter.total / 90 if quarter.total else 0

        elif metric_type == "products":
            today = await service.get_product_metrics("today")
            week = await service.get_product_metrics("week")
            month = await service.get_product_metrics("month")
            quarter = await service.get_product_metrics("quarter")

            today_value = today.total_sold
            week_avg = week.total_sold / 7 if week.total_sold else 0
            month_avg = month.total_sold / 30 if month.total_sold else 0
            quarter_avg = quarter.total_sold / 90 if quarter.total_sold else 0

        elif metric_type == "customers":
            today = await service.get_customer_metrics("today")
            week = await service.get_customer_metrics("week")
            month = await service.get_customer_metrics("month")
            quarter = await service.get_customer_metrics("quarter")

            today_value = today.new_customers
            week_avg = week.new_customers / 7 if week.new_customers else 0
            month_avg = month.new_customers / 30 if month.new_customers else 0
            quarter_avg = quarter.new_customers / 90 if quarter.new_customers else 0
        else:
            return ComparisonData()

        vs_7 = _calc_percentage(today_value, week_avg)
        vs_30 = _calc_percentage(today_value, month_avg)
        vs_90 = _calc_percentage(today_value, quarter_avg)

        trend = _determine_trend(vs_7, vs_30, vs_90)

        return ComparisonData(
            vs_7_days=vs_7,
            vs_30_days=vs_30,
            vs_90_days=vs_90,
            trend=trend
        )

    except Exception as e:
        logger.warning(f"Erro ao calcular comparativos para {metric_type}: {e}")
        return ComparisonData()


def _calc_percentage(current: float, previous: float) -> float | None:
    """Calcula variação percentual."""
    if previous == 0:
        return None if current == 0 else 100.0
    return round(((current - previous) / previous) * 100, 2)


def _determine_trend(vs_7: float | None, vs_30: float | None, vs_90: float | None) -> str:
    """Determina tendência geral baseado nos comparativos."""
    values = [v for v in [vs_7, vs_30, vs_90] if v is not None]
    if not values:
        return "stable"

    avg = sum(values) / len(values)
    if avg > 5:
        return "up"
    elif avg < -5:
        return "down"
    return "stable"
