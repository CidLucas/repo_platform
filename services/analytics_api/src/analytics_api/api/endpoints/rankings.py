# services/analytics_api/src/analytics_api/api/endpoints/rankings.py
from datetime import datetime, timezone

from analytics_api.api.dependencies import get_client_id, get_postgres_repository
from analytics_api.api.helpers import dict_to_ranking_item
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.schemas.metrics import (
    ClientesOverviewResponse,
    FornecedoresOverviewResponse,
    PedidosOverviewResponse,
    ProdutosOverviewResponse,
    RankingItem,
    ChartDataPoint,
    PedidoItem,
    ProdutoRankingReceita,
    ProdutoRankingVolume,
    ProdutoRankingTicket,
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

    # Convert to RankingItem using helper function
    ranking_por_receita = [dict_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("total_revenue", 0), reverse=True)[:10]]
    ranking_por_ticket_medio = [dict_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("ticket_medio", x.get("avg_order_value", 0)), reverse=True)[:10]]
    ranking_por_qtd_media = [dict_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("qtd_media_por_pedido", 0), reverse=True)[:10]]
    ranking_por_frequencia = [dict_to_ranking_item(r) for r in sorted(suppliers, key=lambda x: x.get("frequencia_pedidos_mes", 0), reverse=True)[:10]]

    ranking_produtos_mais_vendidos = [
        ProdutoRankingReceita(
            nome=p.get("product_name", ""),
            receita_total=p.get("total_revenue", 0),
            valor_unitario_medio=p.get("avg_price", 0),
        )
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
    # Calculate cumulative sum for frontend (expects total_cumulativo)
    cumulative_sum = 0
    chart_fornecedores_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_fornecedores_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    regional_data = repo.get_gold_regional(client_id, 'fornecedores_por_regiao')
    chart_fornecedores_por_regiao = [
        ChartDataPoint(name=point['name'], total=point['total'], percentual=point['percentual'])
        for point in regional_data
    ]

    # Calculate growth percentage from time series data
    crescimento_percentual = repo.calculate_growth_from_time_series(client_id, 'fornecedores_no_tempo')

    return FornecedoresOverviewResponse(
        scorecard_total_fornecedores=len(suppliers),
        scorecard_crescimento_percentual=crescimento_percentual,
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

    # Convert to RankingItem using helper function
    ranking_por_receita = [dict_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("lifetime_value", 0), reverse=True)[:10]]
    ranking_por_ticket_medio = [dict_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("ticket_medio", x.get("avg_order_value", 0)), reverse=True)[:10]]
    ranking_por_qtd_pedidos = [dict_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("num_pedidos_unicos", x.get("total_orders", 0)), reverse=True)[:10]]
    ranking_por_cluster_vizu = [dict_to_ranking_item(r) for r in sorted(customers, key=lambda x: x.get("cluster_score", 0), reverse=True)[:10]]

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

    # Time series from Gold (precomputed) with cumulative calculation
    time_data = repo.get_gold_time_series(client_id, 'clientes_no_tempo')
    cumulative_sum = 0
    chart_clientes_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_clientes_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    # Calculate growth percentage from time series data
    crescimento_percentual = repo.calculate_growth_from_time_series(client_id, 'clientes_no_tempo')

    return ClientesOverviewResponse(
        scorecard_total_clientes=len(customers),
        scorecard_ticket_medio_geral=float(ticket_medio_geral),
        scorecard_frequencia_media_geral=float(freq_media_geral),
        scorecard_crescimento_percentual=crescimento_percentual,
        chart_clientes_no_tempo=chart_clientes_no_tempo,
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
        ProdutoRankingReceita(
            nome=p.get("product_name", ""),
            receita_total=p.get("total_revenue", 0),
            valor_unitario_medio=p.get("avg_price", 0),
        )
        for p in sorted(products, key=lambda x: x.get("total_revenue", 0), reverse=True)[:10]
    ]

    ranking_por_volume = [
        ProdutoRankingVolume(
            nome=p.get("product_name", ""),
            quantidade_total=p.get("total_quantity_sold", 0),
            valor_unitario_medio=p.get("avg_price", 0),
        )
        for p in sorted(products, key=lambda x: x.get("total_quantity_sold", 0), reverse=True)[:10]
    ]

    ranking_por_ticket_medio = [
        ProdutoRankingTicket(
            nome=p.get("product_name", ""),
            ticket_medio=p.get("ticket_medio", p.get("avg_price", 0)),
            valor_unitario_medio=p.get("avg_price", 0),
        )
        for p in sorted(products, key=lambda x: x.get("ticket_medio", x.get("avg_price", 0)), reverse=True)[:10]
    ]

    # Time series from Gold (precomputed) with cumulative calculation
    time_data = repo.get_gold_time_series(client_id, 'produtos_no_tempo')
    cumulative_sum = 0
    chart_produtos_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_produtos_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    return ProdutosOverviewResponse(
        scorecard_total_itens_unicos=len(products),
        chart_produtos_no_tempo=chart_produtos_no_tempo,
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

    # Time series from Gold (precomputed) with cumulative calculation
    time_data = repo.get_gold_time_series(client_id, 'pedidos_no_tempo')
    cumulative_sum = 0
    chart_pedidos_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_pedidos_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    return PedidosOverviewResponse(
        scorecard_ticket_medio_por_pedido=scorecard_ticket_medio_por_pedido,
        scorecard_qtd_media_produtos_por_pedido=scorecard_qtd_media_produtos_por_pedido,
        scorecard_taxa_recorrencia_clientes_perc=scorecard_taxa_recorrencia_clientes_perc,
        scorecard_recencia_media_entre_pedidos_dias=scorecard_recencia_media_entre_pedidos_dias,
        chart_pedidos_no_tempo=chart_pedidos_no_tempo,
        ranking_pedidos_por_regiao=ranking_pedidos_por_regiao,
        ultimos_pedidos=ultimos_pedidos,
    )
