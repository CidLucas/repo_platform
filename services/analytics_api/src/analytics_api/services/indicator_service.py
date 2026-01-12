"""
Indicator Service - Leitura de indicadores agregados da camada Gold.

Implementa:
- Growth rate (% vs período anterior)
- Métricas por período (today, week, month)
- Leitura direta de Gold tables (pré-computadas no ETL)

Note: Redis cache removido - Gold tables já são o cache persistente.
"""
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional

from analytics_api.data_access.postgres_repository import PostgresRepository

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
    orders: OrderMetrics | None
    products: ProductMetrics | None
    customers: CustomerMetrics | None
    cached: bool
    generated_at: str
    ttl: int | None


class IndicatorService:
    """
    Serviço de indicadores lendo de Gold tables.

    Lê métricas pré-agregadas da camada Gold (atualizadas no ETL).
    Não usa cache - Gold tables já são rápidas (<10ms por query).
    """

    def __init__(self, repository: PostgresRepository, client_id: str):
        self.repository = repository
        self.client_id = client_id

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
        Lê métricas de pedidos da camada Gold (pré-computadas).

        Note: period parameter não usado - Gold tem agregados all_time.
        Para suportar períodos dinâmicos, seria necessário time_series Gold.
        """
        # Lê diretamente do Gold (sem cache - já é rápido)
        start_date, end_date = self._get_date_range(period)
        prev_start, prev_end = self._get_previous_period_range(period)

        # Query atual - lê Gold table
        current_metrics = self.repository.get_order_metrics_by_date_range(
            self.client_id, start_date, end_date
        )

        # Query período anterior (para growth) - lê Gold table
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

        return metrics

    async def get_product_metrics(self, period: PeriodType = "today") -> ProductMetrics:
        """Lê métricas de produtos da camada Gold (pré-computadas)."""
        start_date, end_date = self._get_date_range(period)

        # Lê diretamente do Gold (sem cache)
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

        return metrics

    async def get_customer_metrics(self, period: PeriodType = "today") -> CustomerMetrics:
        """Lê métricas de clientes da camada Gold (pré-computadas)."""
        start_date, end_date = self._get_date_range(period)

        # Lê diretamente do Gold (sem cache)
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

        return metrics

    async def get_indicators(
        self,
        period: PeriodType = "today",
        metrics: list[str] | None = None
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
