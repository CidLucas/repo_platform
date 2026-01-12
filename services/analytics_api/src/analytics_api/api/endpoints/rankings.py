# services/analytics_api/src/analytics_api/api/endpoints/rankings.py
from datetime import datetime, timezone

from analytics_api.api.dependencies import get_client_id, get_postgres_repository
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.schemas.metrics import (
    ClientesOverviewResponse,
    FornecedoresOverviewResponse,
    PedidosOverviewResponse,
    ProdutosOverviewResponse,
    RankingItem,
    ChartDataPoint,
    PedidoItem,
)
from fastapi import APIRouter, Depends

router = APIRouter()

# --- Endpoint para Módulo FORNECEDORES ---
@router.get(
    "/fornecedores",
    response_model=FornecedoresOverviewResponse,
    summary="Visão Geral Fornecedores (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_fornecedores_overview_endpoint(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """Retorna KPIs, rankings e gráficos para a página de Fornecedores a partir da camada ouro."""

    suppliers = repo.get_gold_suppliers_metrics(client_id) or []
    products = repo.get_gold_products_metrics(client_id) or []

    def _dt(value: datetime | None) -> datetime:
        return value if isinstance(value, datetime) else datetime(1970, 1, 1, tzinfo=timezone.utc)

    def _to_ranking_item(row: dict) -> RankingItem:
        return RankingItem(
            nome=row.get("supplier_name", ""),
            receita_total=float(row.get("total_revenue", 0)),
            quantidade_total=float(row.get("quantidade_total", 0)),
            num_pedidos_unicos=int(row.get("num_pedidos_unicos", row.get("total_orders", 0) or 0)),
            primeira_venda=_dt(row.get("primeira_venda")),
            ultima_venda=_dt(row.get("ultima_venda")),
            ticket_medio=float(row.get("ticket_medio", row.get("avg_order_value", 0) or 0)),
            qtd_media_por_pedido=float(row.get("qtd_media_por_pedido", 0)),
            frequencia_pedidos_mes=float(row.get("frequencia_pedidos_mes", 0)),
            recencia_dias=int(row.get("recencia_dias", 0)),
            valor_unitario_medio=float(row.get("valor_unitario_medio", row.get("avg_price", 0) or 0)),
            cluster_score=float(row.get("cluster_score", 0)),
            cluster_tier=str(row.get("cluster_tier", "") or ""),
        )

    ranking_por_receita = [_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("total_revenue", 0), reverse=True)[:10]]
    ranking_por_ticket_medio = [_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("ticket_medio", x.get("avg_order_value", 0)), reverse=True)[:10]]
    ranking_por_qtd_media = [_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("qtd_media_por_pedido", 0), reverse=True)[:10]]
    ranking_por_frequencia = [_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("frequencia_pedidos_mes", 0), reverse=True)[:10]]

    ranking_produtos_mais_vendidos = [
        {
            "nome": p.get("product_name", ""),
            "receita_total": p.get("total_revenue", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in sorted(products, key=lambda x: x.get("total_revenue", 0), reverse=True)[:10]
    ]

    # Cohort from gold tiers if available
    chart_cohort_fornecedores = []
    if suppliers:
        by_tier: dict[str, int] = {}
        for s in suppliers:
            tier = str(s.get("cluster_tier", "")).strip() or ""
            by_tier[tier] = by_tier.get(tier, 0) + 1
        total = sum(by_tier.values()) or 1
        chart_cohort_fornecedores = [
            ChartDataPoint(name=tier, contagem=count, percentual=(count / total) * 100)
            for tier, count in by_tier.items()
        ]

    # Time/regional charts from Gold (precomputed)
    time_data = repo.get_gold_time_series(client_id, 'fornecedores_no_tempo')
    chart_fornecedores_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in time_data
    ]

    regional_data = repo.get_gold_regional(client_id, 'fornecedores_por_regiao')
    chart_fornecedores_por_regiao = [
        ChartDataPoint(name=point['name'], total=point['total'], percentual=point['percentual'])
        for point in regional_data
    ]

    return FornecedoresOverviewResponse(
        scorecard_total_fornecedores=len(suppliers),
        scorecard_crescimento_percentual=None,
        chart_fornecedores_no_tempo=chart_fornecedores_no_tempo,
        chart_fornecedores_por_regiao=chart_fornecedores_por_regiao,
        chart_cohort_fornecedores=chart_cohort_fornecedores,
        ranking_por_receita=ranking_por_receita,
        ranking_por_qtd_media=ranking_por_qtd_media,
        ranking_por_ticket_medio=ranking_por_ticket_medio,
        ranking_por_frequencia=ranking_por_frequencia,
        ranking_produtos_mais_vendidos=ranking_produtos_mais_vendidos,
    )

# --- Endpoint para Módulo CLIENTES ---
@router.get(
    "/clientes",
    response_model=ClientesOverviewResponse,
    summary="Visão Geral Clientes (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_clientes_overview_endpoint(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """Retorna KPIs, rankings e gráficos para a página de Clientes a partir da camada ouro."""

    customers = repo.get_gold_customers_metrics(client_id) or []

    def _dt(value: datetime | None) -> datetime:
        return value if isinstance(value, datetime) else datetime(1970, 1, 1, tzinfo=timezone.utc)

    def _to_ranking_item(row: dict) -> RankingItem:
        return RankingItem(
            nome=row.get("customer_name", ""),
            receita_total=float(row.get("lifetime_value", 0)),
            quantidade_total=float(row.get("quantidade_total", 0)),
            num_pedidos_unicos=int(row.get("num_pedidos_unicos", row.get("total_orders", 0) or 0)),
            primeira_venda=_dt(row.get("primeira_venda", row.get("first_order_date"))),
            ultima_venda=_dt(row.get("ultima_venda", row.get("last_order_date"))),
            ticket_medio=float(row.get("ticket_medio", row.get("avg_order_value", 0) or 0)),
            qtd_media_por_pedido=float(row.get("qtd_media_por_pedido", 0)),
            frequencia_pedidos_mes=float(row.get("frequencia_pedidos_mes", 0)),
            recencia_dias=int(row.get("recencia_dias", 0)),
            valor_unitario_medio=float(row.get("valor_unitario_medio", row.get("avg_price", 0) or 0)),
            cluster_score=float(row.get("cluster_score", 0)),
            cluster_tier=str(row.get("cluster_tier", "") or ""),
        )

    ranking_por_receita = [_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("lifetime_value", 0), reverse=True)[:10]]
    ranking_por_ticket_medio = [_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("ticket_medio", x.get("avg_order_value", 0)), reverse=True)[:10]]
    ranking_por_qtd_pedidos = [_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("num_pedidos_unicos", x.get("total_orders", 0)), reverse=True)[:10]]
    ranking_por_cluster_vizu = [_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("cluster_score", 0), reverse=True)[:10]]

    chart_cohort_clientes = []
    if customers:
        by_tier: dict[str, int] = {}
        for c in customers:
            tier = str(c.get("cluster_tier", "")).strip() or ""
            by_tier[tier] = by_tier.get(tier, 0) + 1
        total = sum(by_tier.values()) or 1
        chart_cohort_clientes = [
            ChartDataPoint(name=tier, contagem=count, percentual=(count / total) * 100)
            for tier, count in by_tier.items()
        ]

    # Regional charts from Gold (precomputed)
    regional_data = repo.get_gold_regional(client_id, 'clientes_por_regiao')
    chart_clientes_por_regiao = [
        ChartDataPoint(name=point['name'], contagem=point['contagem'], percentual=point['percentual'])
        for point in regional_data
    ]

    ticket_medio_geral = (
        sum(float(c.get("ticket_medio", c.get("avg_order_value", 0) or 0)) for c in customers) / len(customers)
    ) if customers else 0.0
    freq_media_geral = (
        sum(float(c.get("frequencia_pedidos_mes", 0)) for c in customers) / len(customers)
    ) if customers else 0.0

    return ClientesOverviewResponse(
        scorecard_total_clientes=len(customers),
        scorecard_ticket_medio_geral=float(ticket_medio_geral),
        scorecard_frequencia_media_geral=float(freq_media_geral),
        scorecard_crescimento_percentual=None,
        chart_clientes_por_regiao=chart_clientes_por_regiao,
        chart_cohort_clientes=chart_cohort_clientes,
        ranking_por_receita=ranking_por_receita,
        ranking_por_ticket_medio=ranking_por_ticket_medio,
        ranking_por_qtd_pedidos=ranking_por_qtd_pedidos,
        ranking_por_cluster_vizu=ranking_por_cluster_vizu,
    )

# --- Endpoint para Módulo PRODUTOS ---
@router.get(
    "/produtos",
    response_model=ProdutosOverviewResponse,
    summary="Visão Geral Produtos (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_produtos_overview_endpoint(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """Retorna KPIs e rankings para a página de Produtos a partir da camada ouro."""

    products = repo.get_gold_products_metrics(client_id) or []

    ranking_por_receita = [
        {
            "nome": p.get("product_name", ""),
            "receita_total": p.get("total_revenue", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in sorted(products, key=lambda x: x.get("total_revenue", 0), reverse=True)[:10]
    ]

    ranking_por_volume = [
        {
            "nome": p.get("product_name", ""),
            "quantidade_total": p.get("total_quantity_sold", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in sorted(products, key=lambda x: x.get("total_quantity_sold", 0), reverse=True)[:10]
    ]

    ranking_por_ticket_medio = [
        {
            "nome": p.get("product_name", ""),
            "ticket_medio": p.get("ticket_medio", p.get("avg_price", 0)),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in sorted(products, key=lambda x: x.get("ticket_medio", x.get("avg_price", 0)), reverse=True)[:10]
    ]

    return ProdutosOverviewResponse(
        scorecard_total_itens_unicos=len(products),
        ranking_por_receita=ranking_por_receita,
        ranking_por_volume=ranking_por_volume,
        ranking_por_ticket_medio=ranking_por_ticket_medio,
    )

# --- Endpoint para Módulo PEDIDOS ---
@router.get(
    "/pedidos",
    response_model=PedidosOverviewResponse,
    summary="Visão Geral Pedidos (Nível 2)",
    tags=["Nível 2 - Módulos"]
)
def get_pedidos_overview_endpoint(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """Retorna KPIs e lista de últimos pedidos a partir da camada ouro (dados agregados)."""

    orders = repo.get_gold_orders_metrics(client_id) or {}

    scorecard_ticket_medio_por_pedido = float(orders.get("avg_order_value", 0))
    scorecard_qtd_media_produtos_por_pedido = float(orders.get("qtd_media_por_pedido", 0))
    scorecard_taxa_recorrencia_clientes_perc = float(orders.get("taxa_recorrencia", 0))
    scorecard_recencia_media_entre_pedidos_dias = float(orders.get("recencia_dias", 0))

    # Regional and last orders from Gold (precomputed)
    regional_data = repo.get_gold_regional(client_id, 'pedidos_por_regiao')
    ranking_pedidos_por_regiao = [
        ChartDataPoint(name=point['name'], contagem=point['contagem'], percentual=point['percentual'])
        for point in regional_data
    ]

    last_orders_data = repo.get_gold_last_orders(client_id, limit=20)
    ultimos_pedidos = [
        PedidoItem(
            order_id=order['order_id'],
            data_transacao=order['data_transacao'],
            id_cliente=order['id_cliente'],
            ticket_pedido=order['ticket_pedido'],
            qtd_produtos=order['qtd_produtos']
        )
        for order in last_orders_data
    ]

    return PedidosOverviewResponse(
        scorecard_ticket_medio_por_pedido=scorecard_ticket_medio_por_pedido,
        scorecard_qtd_media_produtos_por_pedido=scorecard_qtd_media_produtos_por_pedido,
        scorecard_taxa_recorrencia_clientes_perc=scorecard_taxa_recorrencia_clientes_perc,
        scorecard_recencia_media_entre_pedidos_dias=scorecard_recencia_media_entre_pedidos_dias,
        ranking_pedidos_por_regiao=ranking_pedidos_por_regiao,
        ultimos_pedidos=ultimos_pedidos,
    )
