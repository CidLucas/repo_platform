"""
Indicator Endpoints - Metrics from analytics_v2 star schema.

Optimized: Single query fetches all metrics, no N+1 queries.
"""
import logging
from dataclasses import asdict

from analytics_api.api.dependencies import get_indicator_service
from analytics_api.services.indicator_service import IndicatorService, PeriodType
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/indicators", tags=["Indicators"])


# --- Response Models ---

class ComparisonData(BaseModel):
    """Comparison data vs previous periods."""
    vs_7_days: float | None = None
    vs_30_days: float | None = None
    vs_90_days: float | None = None
    trend: str | None = None


class IndicatorsRequest(BaseModel):
    """Request body for fetching indicators."""
    period: PeriodType = "today"
    metrics: list[str] | None = None
    include_comparisons: bool = Field(False, description="Comparisons not yet implemented in v2")


class OrderMetricsResponse(BaseModel):
    """Order metrics response."""
    total: int
    revenue: float
    avg_order_value: float
    growth_rate: float | None
    by_status: dict
    period: str
    comparisons: ComparisonData | None = None


class ProductMetricsResponse(BaseModel):
    """Product metrics response."""
    total_sold: int
    unique_products: int
    top_sellers: list
    low_stock_alerts: int
    avg_price: float
    period: str
    comparisons: ComparisonData | None = None


class CustomerMetricsResponse(BaseModel):
    """Customer metrics response."""
    total_active: int
    new_customers: int
    returning_customers: int
    avg_lifetime_value: float
    period: str
    comparisons: ComparisonData | None = None


class IndicatorsResponse(BaseModel):
    """Consolidated indicators response."""
    orders: OrderMetricsResponse | None = None
    products: ProductMetricsResponse | None = None
    customers: CustomerMetricsResponse | None = None
    cached: bool
    generated_at: str
    ttl: int | None = None


# --- Endpoints ---

@router.post("", response_model=IndicatorsResponse)
async def get_indicators(
    request: IndicatorsRequest,
    service: IndicatorService = Depends(get_indicator_service)
):
    """
    Fetch aggregated indicators for the specified period.

    Reads from analytics_v2 star schema (fact_sales, dim_product, dim_customer).
    Single optimized query - no N+1 problem.

    **Periods:**
    - `today`: Current day
    - `yesterday`: Previous day
    - `week`: Last 7 days
    - `month`: Last 30 days
    - `quarter`: Last 90 days
    - `year`: Last 365 days

    **Metrics:**
    - `orders`: Total orders, revenue, avg order value, growth rate
    - `products`: Products sold, unique products, top sellers, avg price
    - `customers`: Active customers, new, returning, avg LTV
    """
    result = await service.get_indicators(
        period=request.period,
        metrics=request.metrics
    )

    orders_response = None
    if result.orders:
        orders_response = OrderMetricsResponse(**asdict(result.orders))

    products_response = None
    if result.products:
        products_response = ProductMetricsResponse(**asdict(result.products))

    customers_response = None
    if result.customers:
        customers_response = CustomerMetricsResponse(**asdict(result.customers))

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
    period: PeriodType = Query("today", description="Time period"),
    service: IndicatorService = Depends(get_indicator_service)
):
    """Get only order indicators."""
    metrics = await service.get_order_metrics(period)
    return OrderMetricsResponse(**asdict(metrics))


@router.get("/products", response_model=ProductMetricsResponse)
async def get_product_indicators(
    period: PeriodType = Query("today", description="Time period"),
    service: IndicatorService = Depends(get_indicator_service)
):
    """Get only product indicators."""
    metrics = await service.get_product_metrics(period)
    return ProductMetricsResponse(**asdict(metrics))


@router.get("/customers", response_model=CustomerMetricsResponse)
async def get_customer_indicators(
    period: PeriodType = Query("today", description="Time period"),
    service: IndicatorService = Depends(get_indicator_service)
):
    """Get only customer indicators."""
    metrics = await service.get_customer_metrics(period)
    return CustomerMetricsResponse(**asdict(metrics))
