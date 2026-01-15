"""
Helper functions for API endpoints to reduce code duplication.
"""
from datetime import datetime, timezone

from analytics_api.schemas.metrics import RankingItem


def dict_to_ranking_item(row: dict) -> RankingItem:
    """
    Convert a dict from gold tables to a RankingItem Pydantic model.

    Handles different naming conventions (old vs new columns) and provides safe defaults.

    Args:
        row: Dict from gold_customers, gold_suppliers, or gold_products

    Returns:
        RankingItem with all fields populated
    """
    def _dt(value: datetime | None) -> datetime:
        """Safe datetime conversion with default fallback."""
        return value if isinstance(value, datetime) else datetime(1970, 1, 1, tzinfo=timezone.utc)

    return RankingItem(
        nome=row.get("customer_name") or row.get("supplier_name") or row.get("product_name", ""),
        receita_total=float(row.get("lifetime_value") or row.get("total_revenue", 0)),
        quantidade_total=float(row.get("quantidade_total", 0)),
        num_pedidos_unicos=int(row.get("num_pedidos_unicos") or row.get("total_orders", 0) or 0),
        primeira_venda=_dt(row.get("primeira_venda") or row.get("first_order_date")),
        ultima_venda=_dt(row.get("ultima_venda") or row.get("last_order_date")),
        ticket_medio=float(row.get("ticket_medio") or row.get("avg_order_value", 0) or 0),
        qtd_media_por_pedido=float(row.get("qtd_media_por_pedido", 0)),
        frequencia_pedidos_mes=float(row.get("frequencia_pedidos_mes", 0)),
        recencia_dias=int(row.get("recencia_dias", 0)),
        valor_unitario_medio=float(row.get("valor_unitario_medio") or row.get("avg_price", 0) or 0),
        cluster_score=float(row.get("cluster_score", 0)),
        cluster_tier=str(row.get("cluster_tier") or row.get("customer_type", "") or ""),
    )
