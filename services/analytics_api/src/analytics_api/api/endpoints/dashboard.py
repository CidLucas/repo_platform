# src/analytics_api/api/endpoints/dashboard.py
"""
Dashboard endpoints - Read from analytics_v2 star schema.

These endpoints read pre-computed metrics from the star schema.
They do NOT trigger silver data computation (BigQuery FDW).

To recompute metrics from silver data, use POST /ingest/recompute
"""
from analytics_api.api.dependencies import (
    get_client_id,
    get_postgres_repository,
)
from analytics_api.api.helpers import dict_to_ranking_item
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.schemas.metrics import (
    ChartDataPoint,
    ClientesOverviewResponse,
    FornecedoresOverviewResponse,
    HomeMetricsResponse,
    HomeScorecards,
    ProdutoRankingReceita,
    ProdutoRankingTicket,
    ProdutoRankingVolume,
    ProdutosOverviewResponse,
    RankingItem,
)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from vizu_auth.dependencies.jwt_only import get_jwt_claims

router = APIRouter()


class MeResponse(BaseModel):
    client_id: str


@router.get(
    "/home",
    response_model=HomeMetricsResponse,
    summary="Métricas Agregadas (Nível 1)",
    tags=["Nível 1 - Home"],
)
async def get_home_dashboard(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Retorna os scorecards agregados e gráficos para a página
    principal (Home) do cliente.

    Reads directly from analytics_v2 star schema - NO silver data computation.
    """
    # Get summary counts from star schema
    summary = repo.get_dashboard_summary(client_id)

    # Get rankings from dimension tables
    customers = repo.get_dim_customers(client_id) or []
    suppliers = repo.get_dim_suppliers(client_id) or []
    products = repo.get_dim_products(client_id) or []

    # Get time series data
    time_series_receita = repo.get_v2_time_series(client_id, 'receita_no_tempo')
    time_series_pedidos = repo.get_v2_time_series(client_id, 'pedidos_no_tempo')

    # Calculate growth
    crescimento_receita = repo.calculate_growth_from_time_series(client_id, 'receita_no_tempo')

    # Build rankings
    ranking_clientes = [
        dict_to_ranking_item(c) for c in sorted(customers, key=lambda x: x.get("total_revenue", 0), reverse=True)[:5]
    ]
    ranking_fornecedores = [
        dict_to_ranking_item(s) for s in sorted(suppliers, key=lambda x: x.get("total_revenue", 0), reverse=True)[:5]
    ]
    ranking_produtos = [
        ProdutoRankingReceita(
            nome=p.get("product_name", ""),
            receita_total=p.get("total_revenue", 0),
            valor_unitario_medio=p.get("avg_price", 0),
        )
        for p in sorted(products, key=lambda x: x.get("total_revenue", 0), reverse=True)[:5]
    ]

    # Build chart data
    chart_receita = [
        ChartDataPoint(name=p.get('name', ''), total=p.get('total', 0))
        for p in time_series_receita
    ]
    chart_pedidos = [
        ChartDataPoint(name=p.get('name', ''), total=p.get('total', 0))
        for p in time_series_pedidos
    ]

    # Calculate totals
    total_revenue = sum(c.get("total_revenue", 0) or 0 for c in customers)
    avg_ticket = total_revenue / summary.get("total_orders", 1) if summary.get("total_orders", 0) > 0 else 0

    return HomeMetricsResponse(
        scorecards=HomeScorecards(
            total_pedidos=summary.get("total_orders", 0),
            total_clientes=summary.get("total_customers", 0),
            total_fornecedores=summary.get("total_suppliers", 0),
            total_produtos=summary.get("total_products", 0),
            receita_total=total_revenue,
            ticket_medio=avg_ticket,
            crescimento_receita=crescimento_receita,
        ),
        chart_receita_no_tempo=chart_receita,
        chart_pedidos_no_tempo=chart_pedidos,
        ranking_clientes=ranking_clientes,
        ranking_fornecedores=ranking_fornecedores,
        ranking_produtos=ranking_produtos,
    )


@router.get(
    "/home_gold",
    response_model=HomeMetricsResponse,
    summary="Métricas Agregadas (Nível 1) - View Ouro (Analytics V2)",
    tags=["Nível 1 - Home", "Ouro"],
)
async def get_home_dashboard_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Alias for /home - reads from analytics_v2 star schema.
    Kept for backwards compatibility with frontend.
    """
    return await get_home_dashboard(repo=repo, client_id=client_id)


@router.get(
    "/produtos/gold",
    response_model=ProdutosOverviewResponse,
    summary="Métricas agregadas de produtos - Analytics V2",
    tags=["Produtos", "Ouro"],
)
async def get_products_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Retorna métricas agregadas de produtos do analytics_v2 star schema.
    Reads directly from dim_product - NO silver data computation.
    """
    products = repo.get_dim_products(client_id) or []

    # Build rankings
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
            num_pedidos=p.get("number_of_orders", 0),
        )
        for p in sorted(products, key=lambda x: x.get("total_quantity_sold", 0), reverse=True)[:10]
    ]

    ranking_por_ticket = [
        ProdutoRankingTicket(
            nome=p.get("product_name", ""),
            ticket_medio=p.get("avg_price", 0),
            num_pedidos=p.get("number_of_orders", 0),
        )
        for p in sorted(products, key=lambda x: x.get("avg_price", 0), reverse=True)[:10]
    ]

    # Time series
    time_series = repo.get_v2_time_series(client_id, 'produtos_no_tempo')
    chart_produtos_no_tempo = [
        ChartDataPoint(name=p.get('name', ''), total=p.get('total', 0))
        for p in time_series
    ]

    # Growth
    crescimento = repo.calculate_growth_from_time_series(client_id, 'produtos_no_tempo')

    return ProdutosOverviewResponse(
        scorecard_total_produtos=len(products),
        scorecard_crescimento_percentual=crescimento,
        chart_produtos_no_tempo=chart_produtos_no_tempo,
        ranking_por_receita=ranking_por_receita,
        ranking_por_volume=ranking_por_volume,
        ranking_por_ticket=ranking_por_ticket,
    )


@router.get(
    "/clientes/gold",
    response_model=ClientesOverviewResponse,
    summary="Métricas agregadas de clientes - Analytics V2",
    tags=["Clientes", "Ouro"],
)
async def get_customers_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Retorna métricas agregadas de clientes do analytics_v2 star schema.
    Reads directly from dim_customer - NO silver data computation.
    """
    customers = repo.get_dim_customers(client_id) or []

    # Build rankings
    ranking_por_receita = [dict_to_ranking_item(c) for c in sorted(customers, key=lambda x: x.get("total_revenue", 0), reverse=True)[:10]]
    ranking_por_ticket_medio = [dict_to_ranking_item(c) for c in sorted(customers, key=lambda x: x.get("avg_order_value", 0), reverse=True)[:10]]
    ranking_por_qtd_pedidos = [dict_to_ranking_item(c) for c in sorted(customers, key=lambda x: x.get("total_orders", 0), reverse=True)[:10]]
    ranking_por_cluster_vizu = [dict_to_ranking_item(c) for c in sorted(customers, key=lambda x: x.get("cluster_score", 0), reverse=True)[:10]]

    # Cohort by tier
    chart_cohort_clientes = []
    by_tier: dict[str, int] = {}
    for c in customers:
        tier = str(c.get("cluster_tier", "")).strip() or "C"
        by_tier[tier] = by_tier.get(tier, 0) + 1
    total = sum(by_tier.values()) or 1
    chart_cohort_clientes = [
        ChartDataPoint(name=tier, contagem=count, percentual=(count / total) * 100)
        for tier, count in sorted(by_tier.items())
    ]

    # Time series
    time_series = repo.get_v2_time_series(client_id, 'clientes_no_tempo')
    chart_clientes_no_tempo = [
        ChartDataPoint(name=p.get('name', ''), total=p.get('total', 0))
        for p in time_series
    ]

    # Regional
    regional = repo.get_v2_regional(client_id, 'clientes_por_regiao')
    chart_clientes_por_regiao = [
        ChartDataPoint(name=p.get('name', ''), total=p.get('total', 0), percentual=p.get('percentual', 0))
        for p in regional
    ]

    # Growth
    crescimento = repo.calculate_growth_from_time_series(client_id, 'clientes_no_tempo')

    return ClientesOverviewResponse(
        scorecard_total_clientes=len(customers),
        scorecard_crescimento_percentual=crescimento,
        chart_clientes_no_tempo=chart_clientes_no_tempo,
        chart_clientes_por_regiao=chart_clientes_por_regiao,
        chart_cohort_clientes=chart_cohort_clientes,
        ranking_por_receita=ranking_por_receita,
        ranking_por_ticket_medio=ranking_por_ticket_medio,
        ranking_por_qtd_pedidos=ranking_por_qtd_pedidos,
        ranking_por_cluster_vizu=ranking_por_cluster_vizu,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Retorna o client_id do usuário autenticado",
    tags=["Usuário"],
)
async def get_me(
    claims=Depends(get_jwt_claims),
    repo: PostgresRepository = Depends(get_postgres_repository),
):
    """
    Retorna o client_id do usuário autenticado (cria registro se necessário).

    Uses JWT-only authentication to avoid circular dependency:
    - Validates JWT and extracts Supabase user ID from sub claim
    - Creates a clientes_vizu record if it doesn't exist yet
    - Returns the actual client_id from clientes_vizu table
    """
    if not claims.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado."
        )

    try:
        actual_client_id = repo.ensure_cliente_vizu_exists(
            external_user_id=claims.sub,
            email=claims.email,
        )
        return MeResponse(client_id=actual_client_id)
    except Exception as e:
        import logging
        logging.error(f"Failed to get/create clientes_vizu record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter client_id do usuário."
        )


# =========================================================================
# Materialized View Endpoints - Fast pre-computed data
# =========================================================================

@router.get(
    "/mv/customers",
    summary="Customer summary from materialized view",
    tags=["Materialized Views"],
)
async def get_mv_customers(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Returns customer summary data from mv_customer_summary.
    Fast pre-computed aggregations - no joins required.
    """
    data = repo.get_mv_customer_summary(client_id)
    return {"customers": data, "total": len(data)}


@router.get(
    "/mv/products",
    summary="Product summary from materialized view",
    tags=["Materialized Views"],
)
async def get_mv_products(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Returns product summary data from mv_product_summary.
    Fast pre-computed aggregations - no joins required.
    """
    data = repo.get_mv_product_summary(client_id)
    return {"products": data, "total": len(data)}


@router.get(
    "/mv/monthly-sales",
    summary="Monthly sales trend from materialized view",
    tags=["Materialized Views"],
)
async def get_mv_monthly_sales(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Returns monthly sales trend from mv_monthly_sales_trend.
    Perfect for time-series charts (revenue, orders, customers by month).
    """
    data = repo.get_mv_monthly_sales_trend(client_id)
    return {"monthly_sales": data, "total_months": len(data)}


@router.get(
    "/mv/summary",
    summary="Complete dashboard summary from materialized views",
    tags=["Materialized Views"],
)
async def get_mv_dashboard_summary(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
):
    """
    Returns combined dashboard summary from all materialized views.
    Includes: totals, monthly trend, top customers, top products.
    """
    return repo.get_mv_dashboard_summary(client_id)


@router.get(
    "/clientes/geo-clusters",
    summary="Agrega clientes por localização geográfica",
    tags=["Clientes", "Ouro"],
)
async def get_customers_geo_clusters(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
    group_by: str = "state"
):
    """
    Retorna clusters de clientes agrupados por localização (estado, cidade ou CEP).
    Reads from analytics_v2 star schema - NO silver data computation.
    """
    customers = repo.get_dim_customers(client_id) or []

    if not customers:
        return {"clusters": [], "center": [-14.2350, -51.9253], "max_count": 0}

    # Brazilian state coordinates (approximate centers)
    state_coords = {
        "AC": [-9.0238, -70.8120], "AL": [-9.5713, -36.7820], "AP": [1.4100, -51.7700],
        "AM": [-3.4168, -65.8561], "BA": [-12.5797, -41.7007], "CE": [-5.4984, -39.3206],
        "DF": [-15.7998, -47.8645], "ES": [-19.1834, -40.3089], "GO": [-15.8270, -49.8362],
        "MA": [-4.9609, -45.2744], "MT": [-12.6819, -56.9211], "MS": [-20.7722, -54.7852],
        "MG": [-18.5122, -44.5550], "PA": [-1.9981, -54.9306], "PB": [-7.2399, -36.7820],
        "PR": [-24.8980, -51.4010], "PE": [-8.8137, -36.9541], "PI": [-6.6000, -42.2800],
        "RJ": [-22.9099, -43.2095], "RN": [-5.4026, -36.9541], "RS": [-30.0346, -51.2177],
        "RO": [-10.9472, -62.8256], "RR": [1.9910, -61.3300], "SC": [-27.2423, -50.2189],
        "SP": [-23.5329, -46.6395], "SE": [-10.5741, -37.3857], "TO": [-10.1753, -48.2982]
    }

    clusters = {}

    if group_by == "state":
        for c in customers:
            uf = c.get('endereco_uf') or "UNKNOWN"
            if uf not in clusters:
                clusters[uf] = {
                    "location": uf,
                    "count": 0,
                    "total_revenue": 0,
                    "coordinates": state_coords.get(uf, [-14.2350, -51.9253])
                }
            clusters[uf]["count"] += 1
            clusters[uf]["total_revenue"] += c.get("total_revenue", 0) or 0

    elif group_by == "city":
        for c in customers:
            city = c.get('endereco_cidade') or "UNKNOWN"
            uf = c.get('endereco_uf') or "UNKNOWN"
            key = f"{city}-{uf}"
            if key not in clusters:
                clusters[key] = {
                    "location": f"{city}, {uf}",
                    "count": 0,
                    "total_revenue": 0,
                    "coordinates": state_coords.get(uf, [-14.2350, -51.9253])
                }
            clusters[key]["count"] += 1
            clusters[key]["total_revenue"] += c.get("total_revenue", 0) or 0

    # Convert to list and sort by count
    cluster_list = sorted(clusters.values(), key=lambda x: x["count"], reverse=True)

    center = cluster_list[0]["coordinates"] if cluster_list else [-14.2350, -51.9253]
    max_count = cluster_list[0]["count"] if cluster_list else 0

    return {
        "clusters": cluster_list,
        "center": center,
        "max_count": max_count,
        "total_clusters": len(cluster_list)
    }
