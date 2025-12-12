"""
Indicator Service - Cálculos de indicadores agregados com cache.

Implementa:
- Growth rate (% vs período anterior)
- Métricas por período (today, week, month)
- Aggregations com cache Redis
"""
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Literal

from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.cache_service import CacheService, cache_service

logger = logging.getLogger(__name__)

# Tipos de período suportados
PeriodType = Literal["today", "yesterday", "week", "month", "quarter", "year"]


@dataclass
class OrderMetrics:
    """Métricas de pedidos."""
    total: int
    revenue: float
    avg_order_value: float
    growth_rate: float | None  # % em relação ao período anterior
    by_status: dict
    period: str


@dataclass
class ProductMetrics:
    """Métricas de produtos."""
    total_sold: int
    unique_products: int
    top_sellers: list
    low_stock_alerts: int
    avg_price: float
    period: str


@dataclass
class CustomerMetrics:
    """Métricas de clientes."""
    total_active: int
    new_customers: int
    returning_customers: int
    avg_lifetime_value: float
    period: str


@dataclass
class IndicatorsResponse:
    """Resposta consolidada de indicadores."""
    orders: Optional[OrderMetrics]
    products: Optional[ProductMetrics]
    customers: Optional[CustomerMetrics]
    cached: bool
    generated_at: str
    ttl: Optional[int]


class IndicatorService:
    """
    Serviço de indicadores com cache Redis.

    Calcula métricas agregadas e as armazena em cache para
    evitar queries pesadas repetidas.
    """

    def __init__(self, repository: PostgresRepository, client_id: str):
        self.repository = repository
        self.client_id = client_id
        self.cache = cache_service

    def _get_date_range(self, period: PeriodType) -> tuple[datetime, datetime]:
        """Retorna (start_date, end_date) para o período."""
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

    def _get_previous_period_range(self, period: PeriodType) -> tuple[datetime, datetime]:
        """Retorna range do período anterior para cálculo de growth."""
        start, end = self._get_date_range(period)
        duration = end - start
        return (start - duration, start)

    async def get_order_metrics(self, period: PeriodType = "today") -> OrderMetrics:
        """
        Calcula métricas de pedidos para o período.

        Usa cache se disponível.
        """
        cache_key = CacheService.build_key("orders", self.client_id, period)

        # Tenta buscar do cache
        cached = await self.cache.get(cache_key)
        if cached:
            return OrderMetrics(**cached["data"])

        # Calcula métricas
        start_date, end_date = self._get_date_range(period)
        prev_start, prev_end = self._get_previous_period_range(period)

        # Query atual
        current_metrics = self.repository.get_order_metrics_by_date_range(
            self.client_id, start_date, end_date
        )

        # Query período anterior (para growth)
        previous_metrics = self.repository.get_order_metrics_by_date_range(
            self.client_id, prev_start, prev_end
        )

        # Calcula growth rate
        growth_rate = None
        if previous_metrics.get("total", 0) > 0:
            current_total = current_metrics.get("total", 0)
            prev_total = previous_metrics.get("total", 0)
            growth_rate = ((current_total - prev_total) / prev_total) * 100

        metrics = OrderMetrics(
            total=current_metrics.get("total", 0),
            revenue=current_metrics.get("revenue", 0.0),
            avg_order_value=current_metrics.get("avg_order_value", 0.0),
            growth_rate=round(growth_rate, 2) if growth_rate else None,
            by_status=current_metrics.get("by_status", {}),
            period=period
        )

        # Armazena no cache
        await self.cache.set(cache_key, asdict(metrics))

        return metrics

    async def get_product_metrics(self, period: PeriodType = "today") -> ProductMetrics:
        """Calcula métricas de produtos para o período."""
        cache_key = CacheService.build_key("products", self.client_id, period)

        cached = await self.cache.get(cache_key)
        if cached:
            return ProductMetrics(**cached["data"])

        start_date, end_date = self._get_date_range(period)

        product_data = self.repository.get_product_metrics_by_date_range(
            self.client_id, start_date, end_date
        )

        metrics = ProductMetrics(
            total_sold=product_data.get("total_sold", 0),
            unique_products=product_data.get("unique_products", 0),
            top_sellers=product_data.get("top_sellers", [])[:10],
            low_stock_alerts=product_data.get("low_stock_alerts", 0),
            avg_price=product_data.get("avg_price", 0.0),
            period=period
        )

        await self.cache.set(cache_key, asdict(metrics))
        return metrics

    async def get_customer_metrics(self, period: PeriodType = "today") -> CustomerMetrics:
        """Calcula métricas de clientes para o período."""
        cache_key = CacheService.build_key("customers", self.client_id, period)

        cached = await self.cache.get(cache_key)
        if cached:
            return CustomerMetrics(**cached["data"])

        start_date, end_date = self._get_date_range(period)

        customer_data = self.repository.get_customer_metrics_by_date_range(
            self.client_id, start_date, end_date
        )

        metrics = CustomerMetrics(
            total_active=customer_data.get("total_active", 0),
            new_customers=customer_data.get("new_customers", 0),
            returning_customers=customer_data.get("returning_customers", 0),
            avg_lifetime_value=customer_data.get("avg_lifetime_value", 0.0),
            period=period
        )

        await self.cache.set(cache_key, asdict(metrics))
        return metrics

    async def get_indicators(
        self,
        period: PeriodType = "today",
        metrics: Optional[list[str]] = None
    ) -> IndicatorsResponse:
        """
        Retorna indicadores consolidados.

        Args:
            period: Período para cálculo
            metrics: Lista de métricas a incluir ["orders", "products", "customers"]
                     Se None, retorna todas.
        """
        if metrics is None:
            metrics = ["orders", "products", "customers"]

        orders = None
        products = None
        customers = None
        cached = False
        ttl = None

        if "orders" in metrics:
            orders = await self.get_order_metrics(period)

        if "products" in metrics:
            products = await self.get_product_metrics(period)

        if "customers" in metrics:
            customers = await self.get_customer_metrics(period)

        return IndicatorsResponse(
            orders=orders,
            products=products,
            customers=customers,
            cached=cached,
            generated_at=datetime.utcnow().isoformat(),
            ttl=ttl
        )
