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

    def _filter_records_by_date_range(self, records: list[dict], start_date: datetime, end_date: datetime) -> list[dict]:
        """
        Filtra registros mensais que intersectam com o período especificado.

        Args:
            records: Lista de registros mensais do gold_orders
            start_date: Data inicial do período
            end_date: Data final do período

        Returns:
            Lista filtrada de registros que intersectam com o período
        """
        from datetime import timezone

        filtered = []
        for record in records:
            period_start = record.get("period_start")
            period_end = record.get("period_end")

            if not period_start or not period_end:
                continue

            # Garante timezone-aware datetimes
            if period_start.tzinfo is None:
                period_start = period_start.replace(tzinfo=timezone.utc)
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # Verifica se há interseção entre os períodos
            # Interseção existe se: period_start < end_date AND period_end > start_date
            if period_start < end_date and period_end > start_date:
                filtered.append(record)

        return filtered

    def _filter_time_series_by_date_range(self, records: list[dict], start_date: datetime, end_date: datetime) -> list[dict]:
        """
        Filtra registros da gold_time_series que intersectam com o período especificado.

        Args:
            records: Lista de registros da analytics_gold_time_series
            start_date: Data inicial do período
            end_date: Data final do período

        Returns:
            Lista filtrada de registros cujo period_date cai dentro do período
        """
        from datetime import timezone, timedelta
        from dateutil.relativedelta import relativedelta

        filtered = []
        for record in records:
            period_date = record.get("period_date")

            if not period_date:
                continue

            # Converte date para datetime se necessário
            if isinstance(period_date, datetime):
                period_start = period_date
            else:
                period_start = datetime.combine(period_date, datetime.min.time())

            # O registro representa um mês inteiro (do dia 1 ao último dia do mês)
            period_end = period_start + relativedelta(months=1)

            # Garante timezone-aware datetimes
            if period_start.tzinfo is None:
                period_start = period_start.replace(tzinfo=timezone.utc)
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # Verifica se há interseção entre os períodos
            # Interseção existe se: period_start < end_date AND period_end > start_date
            if period_start < end_date and period_end > start_date:
                filtered.append(record)

        return filtered

    async def get_order_metrics(self, period: PeriodType = "today") -> OrderMetrics:
        """
        Lê métricas de pedidos da gold_orders com date filtering e growth.

        Usa gold_orders monthly data que inclui revenue, não gold_time_series.
        """
        start_date, end_date = self._get_date_range(period)
        prev_start, prev_end = self._get_previous_period_range(period)

        # Busca registros mensais do gold_orders (tem revenue)
        monthly_records = self.repository.get_gold_orders_time_series(self.client_id)

        if not monthly_records:
            logger.warning(f"No monthly records found for client {self.client_id}")
            return OrderMetrics(
                total=0,
                revenue=0.0,
                avg_order_value=0.0,
                growth_rate=None,
                by_status={},
                period=period
            )

        # Filtra registros mensais por período
        current_records = self._filter_records_by_date_range(monthly_records, start_date, end_date)
        previous_records = self._filter_records_by_date_range(monthly_records, prev_start, prev_end)

        # Agrega métricas do período atual
        current_total = sum(r.get("total_orders", 0) for r in current_records)
        current_revenue = sum(r.get("total_revenue", 0.0) for r in current_records)
        current_avg = current_revenue / current_total if current_total > 0 else 0.0

        # Agrega métricas do período anterior
        prev_total = sum(r.get("total_orders", 0) for r in previous_records)

        # Calcula growth rate
        growth_rate = None
        if prev_total > 0:
            growth_rate = ((current_total - prev_total) / prev_total) * 100

        logger.info(f"Order metrics for period '{period}': {current_total} orders, growth: {growth_rate}%")

        metrics = OrderMetrics(
            total=current_total,
            revenue=current_revenue,
            avg_order_value=current_avg,
            growth_rate=round(growth_rate, 2) if growth_rate else None,
            by_status={},
            period=period
        )

        return metrics

    async def get_product_metrics(self, period: PeriodType = "today") -> ProductMetrics:
        """
        Lê métricas de produtos da gold_products com date filtering.

        Filtra produtos por ultima_venda e agrega métricas.
        """
        start_date, end_date = self._get_date_range(period)

        # Busca e agrega produtos filtrados por date range
        product_data = self.repository.get_gold_products_aggregated(
            self.client_id, start_date, end_date
        )

        logger.info(f"Product metrics for period '{period}': {product_data.get('unique_products', 0)} products")

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
        """
        Lê métricas de clientes da gold_customers com date filtering.

        Filtra clientes por ultima_compra e primeira_compra para calcular new/returning.
        """
        start_date, end_date = self._get_date_range(period)

        # Busca e agrega clientes filtrados por date range
        customer_data = self.repository.get_gold_customers_aggregated(
            self.client_id, start_date, end_date
        )

        logger.info(f"Customer metrics for period '{period}': {customer_data.get('total_active', 0)} customers")

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
