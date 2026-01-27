"""
Indicator Service - Reads metrics from analytics_v2 star schema.

Optimized for performance:
- Single query fetches all metrics (orders, products, customers)
- No legacy gold tables - uses star schema directly
- Minimal logging to reduce noise
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from analytics_api.data_access.postgres_repository import PostgresRepository

logger = logging.getLogger(__name__)

# Supported period types
PeriodType = Literal["today", "yesterday", "week", "month", "quarter", "year"]


@dataclass
class OrderMetrics:
    """Order metrics from fact_sales."""
    total: int
    revenue: float
    avg_order_value: float
    growth_rate: float | None
    by_status: dict
    period: str


@dataclass
class ProductMetrics:
    """Product metrics from dim_product."""
    total_sold: int
    unique_products: int
    top_sellers: list
    low_stock_alerts: int
    avg_price: float
    period: str


@dataclass
class CustomerMetrics:
    """Customer metrics from dim_customer."""
    total_active: int
    new_customers: int
    returning_customers: int
    avg_lifetime_value: float
    period: str


@dataclass
class IndicatorsResponse:
    """Consolidated indicators response."""
    orders: OrderMetrics | None
    products: ProductMetrics | None
    customers: CustomerMetrics | None
    cached: bool
    generated_at: str
    ttl: int | None


class IndicatorService:
    """
    Reads indicator metrics from analytics_v2 star schema.

    Uses a single optimized query to fetch all metrics at once,
    avoiding the N+1 query problem of the legacy implementation.
    """

    def __init__(self, repository: PostgresRepository, client_id: str):
        self.repository = repository
        self.client_id = client_id

    def _get_date_range(self, period: PeriodType) -> tuple[datetime, datetime]:
        """Get (start_date, end_date) for the specified period."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        ranges = {
            "today": (today_start, now),
            "yesterday": (today_start - timedelta(days=1), today_start),
            "week": (today_start - timedelta(days=7), now),
            "month": (today_start - timedelta(days=30), now),
            "quarter": (today_start - timedelta(days=90), now),
            "year": (today_start - timedelta(days=365), now),
        }
        return ranges.get(period, ranges["today"])

    async def get_indicators(
        self,
        period: PeriodType = "today",
        metrics: list[str] | None = None
    ) -> IndicatorsResponse:
        """
        Fetch all indicators in a single optimized query.

        Args:
            period: Time period for filtering fact_sales
            metrics: List of metrics to include ["orders", "products", "customers"]
                     If None, returns all.

        Returns:
            IndicatorsResponse with requested metrics
        """
        if metrics is None:
            metrics = ["orders", "products", "customers"]

        start_date, end_date = self._get_date_range(period)

        # Single optimized query for all metrics
        data = self.repository.get_all_indicators(
            self.client_id,
            start_date=start_date,
            end_date=end_date
        )

        orders = None
        products = None
        customers = None

        if "orders" in metrics and data.get("orders"):
            orders = OrderMetrics(
                total=data["orders"].get("total", 0),
                revenue=data["orders"].get("revenue", 0.0),
                avg_order_value=data["orders"].get("avg_order_value", 0.0),
                growth_rate=data["orders"].get("growth_rate"),
                by_status=data["orders"].get("by_status", {}),
                period=period
            )

        if "products" in metrics and data.get("products"):
            products = ProductMetrics(
                total_sold=data["products"].get("total_sold", 0),
                unique_products=data["products"].get("unique_products", 0),
                top_sellers=data["products"].get("top_sellers", [])[:10],
                low_stock_alerts=data["products"].get("low_stock_alerts", 0),
                avg_price=data["products"].get("avg_price", 0.0),
                period=period
            )

        if "customers" in metrics and data.get("customers"):
            customers = CustomerMetrics(
                total_active=data["customers"].get("total_active", 0),
                new_customers=data["customers"].get("new_customers", 0),
                returning_customers=data["customers"].get("returning_customers", 0),
                avg_lifetime_value=data["customers"].get("avg_lifetime_value", 0.0),
                period=period
            )

        logger.debug(f"Indicators fetched for {self.client_id}: period={period}")

        return IndicatorsResponse(
            orders=orders,
            products=products,
            customers=customers,
            cached=False,
            generated_at=datetime.utcnow().isoformat(),
            ttl=None
        )

    async def get_order_metrics(self, period: PeriodType = "today") -> OrderMetrics:
        """Get only order metrics."""
        result = await self.get_indicators(period=period, metrics=["orders"])
        return result.orders or OrderMetrics(
            total=0, revenue=0.0, avg_order_value=0.0,
            growth_rate=None, by_status={}, period=period
        )

    async def get_product_metrics(self, period: PeriodType = "today") -> ProductMetrics:
        """Get only product metrics."""
        result = await self.get_indicators(period=period, metrics=["products"])
        return result.products or ProductMetrics(
            total_sold=0, unique_products=0, top_sellers=[],
            low_stock_alerts=0, avg_price=0.0, period=period
        )

    async def get_customer_metrics(self, period: PeriodType = "today") -> CustomerMetrics:
        """Get only customer metrics."""
        result = await self.get_indicators(period=period, metrics=["customers"])
        return result.customers or CustomerMetrics(
            total_active=0, new_customers=0, returning_customers=0,
            avg_lifetime_value=0.0, period=period
        )
