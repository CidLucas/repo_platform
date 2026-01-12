# src/analytics_api/api/endpoints/dashboard.py
import pandas as pd
from analytics_api.api.dependencies import (
    get_client_id,
    get_metric_service,
    get_postgres_repository,
)
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.schemas.metrics import HomeMetricsResponse
from analytics_api.services.metric_service import MetricService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from vizu_auth.dependencies.jwt_only import get_jwt_claims
from vizu_auth.fastapi import create_auth_dependency

router = APIRouter()

# Dependência de autenticação (ajuste conforme sua factory real)
auth_dependency = create_auth_dependency(
    api_key_lookup_fn=lambda key: None,  # Substitua por função real se usar API Key
    external_user_lookup_fn=None,
)


class MeResponse(BaseModel):
    client_id: str


@router.get(
    "/home",
    # RESPONSE_MODEL ATUALIZADO: Corresponde ao schema novo
    response_model=HomeMetricsResponse,
    summary="Métricas Agregadas (Nível 1)",
    tags=["Nível 1 - Home"],
)
async def get_home_dashboard(service: MetricService = Depends(get_metric_service)):
    """
    Retorna os scorecards agregados e gráficos para a página
    principal (Home) do cliente.

    Client ID is extracted from:
    - Query param: ?client_id=xxx
    - Header: X-Client-ID
    - JWT token: sub claim
    """
    # Nenhuma mudança aqui, a função já era get_home_metrics
    metrics_data = service.get_home_metrics()
    return metrics_data


@router.get(
    "/home_gold",
    response_model=HomeMetricsResponse,
    summary="Métricas Agregadas (Nível 1) - View Ouro",
    tags=["Nível 1 - Home", "Ouro"],
)
async def get_home_dashboard_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna os scorecards agregados e gráficos para a página principal (Home) do cliente,
    consultando todas as views ouro (orders, suppliers, customers, products).

    Requires client_id for data isolation (RLS).
    """
    # Get data from all gold tables filtered by client_id
    orders_data = repo.get_gold_orders_metrics(client_id)
    suppliers_data = repo.get_gold_suppliers_metrics(client_id)
    customers_data = repo.get_gold_customers_metrics(client_id)
    products_data = repo.get_gold_products_metrics(client_id)

    # Build scorecards
    scorecards = {
        "receita_total": float(orders_data.get("total_revenue", 0)),
        "total_pedidos": int(orders_data.get("total_orders", 0)),
        "total_fornecedores": len(suppliers_data) if suppliers_data else 0,
        "total_clientes": len(customers_data) if customers_data else 0,
        "total_produtos": len(products_data) if products_data else 0,
        "total_regioes": 0,  # TODO: Calculate from analytics_silver if needed
    }

    # Build charts (empty for now, can be populated later)
    charts = []

    return {
        "scorecards": scorecards,
        "charts": charts
    }


@router.get(
    "/produtos/gold",
    summary="Métricas agregadas de produtos - View Ouro",
    tags=["Produtos", "Ouro"],
)
async def get_products_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna métricas agregadas de produtos a partir da view ouro (analytics_gold_products).
    Transforma os dados brutos em ProdutosOverviewResponse com scorecards e rankings.

    Requires client_id for data isolation (RLS).
    """
    products_data = repo.get_gold_products_metrics(client_id)

    # Calculate total unique items
    total_itens_unicos = len(products_data) if products_data else 0

    # Sort by total revenue
    ranking_por_receita_raw = sorted(
        products_data,
        key=lambda x: x.get("total_revenue", 0),
        reverse=True
    )[:10] if products_data else []

    # Sort by volume (quantity sold)
    ranking_por_volume_raw = sorted(
        products_data,
        key=lambda x: x.get("total_quantity_sold", 0),
        reverse=True
    )[:10] if products_data else []

    # Sort by average price (ticket medio)
    ranking_por_ticket_medio_raw = sorted(
        products_data,
        key=lambda x: x.get("avg_price", 0),
        reverse=True
    )[:10] if products_data else []

    # Transform to expected format: list of dicts with (nome, receita_total, valor_unitario_medio)
    ranking_por_receita = [
        {
            "nome": p.get("product_name", ""),
            "receita_total": p.get("total_revenue", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in ranking_por_receita_raw
    ]

    # Transform to expected format: list of dicts with (nome, quantidade_total, valor_unitario_medio)
    ranking_por_volume = [
        {
            "nome": p.get("product_name", ""),
            "quantidade_total": p.get("total_quantity_sold", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in ranking_por_volume_raw
    ]

    # Transform to expected format: list of dicts with (nome, ticket_medio, valor_unitario_medio)
    ranking_por_ticket_medio = [
        {
            "nome": p.get("product_name", ""),
            "ticket_medio": p.get("avg_price", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in ranking_por_ticket_medio_raw
    ]

    return {
        "scorecard_total_itens_unicos": total_itens_unicos,
        "ranking_por_receita": ranking_por_receita,
        "ranking_por_volume": ranking_por_volume,
        "ranking_por_ticket_medio": ranking_por_ticket_medio,
    }


@router.get(
    "/clientes/gold",
    summary="Métricas agregadas de clientes - View Ouro",
    tags=["Clientes", "Ouro"],
)
async def get_customers_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna métricas agregadas de clientes a partir da view ouro (analytics_gold_customers).
    Calcula charts de região a partir da view silver (transações).

    Requires client_id for data isolation (RLS).
    """
    customers_data = repo.get_gold_customers_metrics(client_id)

    # Calculate aggregated metrics
    total_clientes = len(customers_data) if customers_data else 0

    # Calculate average ticket and frequency if data exists
    if customers_data:
        total_lifetime_value = sum(c.get("lifetime_value", 0) for c in customers_data)
        total_orders = sum(c.get("total_orders", 0) for c in customers_data)

        ticket_medio = (total_lifetime_value / total_orders) if total_orders > 0 else 0
        frequencia_media = (total_orders / total_clientes) if total_clientes > 0 else 0
    else:
        ticket_medio = 0
        frequencia_media = 0

    # Sort by lifetime value for ranking
    ranking_por_receita = sorted(
        customers_data,
        key=lambda x: x.get("lifetime_value", 0),
        reverse=True
    )[:10] if customers_data else []

    # Sort by average order value for ticket medio ranking
    ranking_por_ticket_medio = sorted(
        customers_data,
        key=lambda x: x.get("avg_order_value", 0),
        reverse=True
    )[:10] if customers_data else []

    # Sort by total orders for quantidade ranking
    ranking_por_qtd_pedidos = sorted(
        customers_data,
        key=lambda x: x.get("total_orders", 0),
        reverse=True
    )[:10] if customers_data else []

    # Sort by customer type for cluster ranking
    ranking_por_cluster_vizu = sorted(
        customers_data,
        key=lambda x: (x.get("customer_type", ""), x.get("lifetime_value", 0)),
        reverse=True
    )[:10] if customers_data else []

    # Get silver data for charts (has geographic columns)
    df_silver = repo.get_silver_dataframe(client_id)

    # Calculate regional chart from silver data
    chart_clientes_por_regiao = []
    state_col = None
    for col in ['receiverstateuf', 'receiver_estado', 'receiver_state']:
        if col in df_silver.columns:
            state_col = col
            break

    if state_col and 'receiver_nome' in df_silver.columns:
        # Group by state and count unique customers
        regional_groups = df_silver.groupby(state_col)['receiver_nome'].nunique()
        total_by_region = regional_groups.sum()
        chart_clientes_por_regiao = [
            {
                "name": state,
                "contagem": int(count),
                "percentual": float((count / total_by_region) * 100)
            }
            for state, count in regional_groups.items()
        ]

    # Calculate cohort chart from gold data if cluster_tier exists
    chart_cohort_clientes = []
    if customers_data and len(customers_data) > 0:
        df_customers = pd.DataFrame(customers_data)
        if 'cluster_tier' in df_customers.columns:
            cohort_groups = df_customers.groupby('cluster_tier').size()
            total_by_cohort = cohort_groups.sum()
            chart_cohort_clientes = [
                {
                    "name": tier,
                    "contagem": int(count),
                    "percentual": float((count / total_by_cohort) * 100)
                }
                for tier, count in cohort_groups.items()
            ]

    return {
        "scorecard_total_clientes": total_clientes,
        "scorecard_ticket_medio_geral": float(ticket_medio),
        "scorecard_frequencia_media_geral": float(frequencia_media),
        "scorecard_crescimento_percentual": None,
        "chart_clientes_por_regiao": chart_clientes_por_regiao,
        "chart_cohort_clientes": chart_cohort_clientes,
        "ranking_por_receita": ranking_por_receita,
        "ranking_por_ticket_medio": ranking_por_ticket_medio,
        "ranking_por_qtd_pedidos": ranking_por_qtd_pedidos,
        "ranking_por_cluster_vizu": ranking_por_cluster_vizu,
    }


@router.get(
    "/fornecedores/gold",
    summary="Métricas agregadas de fornecedores - View Ouro",
    tags=["Fornecedores", "Ouro"],
)
async def get_suppliers_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna métricas agregadas de fornecedores a partir da view ouro (analytics_gold_suppliers).
    Calcula charts de região a partir da view silver (transações).

    Requires client_id for data isolation (RLS).
    """
    suppliers_data = repo.get_gold_suppliers_metrics(client_id)
    products_data = repo.get_gold_products_metrics(client_id)

    # Calculate aggregated metrics
    total_fornecedores = len(suppliers_data) if suppliers_data else 0

    # Sort by total revenue for ranking
    ranking_por_receita = sorted(
        suppliers_data,
        key=lambda x: x.get("total_revenue", 0),
        reverse=True
    )[:10] if suppliers_data else []

    # Sort by avg order value for ticket medio ranking
    ranking_por_qtd_media = sorted(
        suppliers_data,
        key=lambda x: x.get("avg_order_value", 0),
        reverse=True
    )[:10] if suppliers_data else []

    # Sort by unique products
    ranking_por_ticket_medio = sorted(
        suppliers_data,
        key=lambda x: x.get("unique_products", 0),
        reverse=True
    )[:10] if suppliers_data else []

    # Sort by order frequency (total_orders / time_period)
    ranking_por_frequencia = sorted(
        suppliers_data,
        key=lambda x: x.get("total_orders", 0),
        reverse=True
    )[:10] if suppliers_data else []

    # Get top products by revenue
    ranking_produtos_mais_vendidos = sorted(
        products_data,
        key=lambda x: x.get("total_revenue", 0),
        reverse=True
    )[:10] if products_data else []

    # Transform to expected format (nome, receita_total, valor_unitario_medio)
    produtos_vendidos_formatted = [
        {
            "nome": p.get("product_name", ""),
            "receita_total": p.get("total_revenue", 0),
            "valor_unitario_medio": p.get("avg_price", 0),
        }
        for p in ranking_produtos_mais_vendidos
    ]

    # Get silver data for charts (has geographic and temporal columns)
    df_silver = repo.get_silver_dataframe(client_id)

    # Calculate regional chart from silver data
    chart_fornecedores_por_regiao = []
    state_col = None
    for col in ['emitterstateuf', 'emitter_estado', 'emitter_state']:
        if col in df_silver.columns:
            state_col = col
            break

    if state_col and 'emitter_nome' in df_silver.columns:
        # Group by state and count unique suppliers
        regional_groups = df_silver.groupby(state_col)['emitter_nome'].nunique()
        total_by_region = regional_groups.sum()
        chart_fornecedores_por_regiao = [
            {
                "name": state,
                "total": int(count),
                "percentual": float((count / total_by_region) * 100)
            }
            for state, count in regional_groups.items()
        ]

    # Calculate time series from silver data
    chart_fornecedores_no_tempo = []
    if 'data_transacao' in df_silver.columns and 'emitter_nome' in df_silver.columns:
        # Convert to datetime and group by month
        df_silver['ano_mes'] = pd.to_datetime(df_silver['data_transacao']).dt.to_period('M').astype(str)
        # Cumulative count of unique suppliers over time
        time_series = df_silver.groupby('ano_mes')['emitter_nome'].nunique().cumsum()
        chart_fornecedores_no_tempo = [
            {
                "name": month,
                "total_cumulativo": int(count)
            }
            for month, count in time_series.items()
        ]

    return {
        "scorecard_total_fornecedores": total_fornecedores,
        "scorecard_crescimento_percentual": None,
        "chart_fornecedores_no_tempo": chart_fornecedores_no_tempo,
        "chart_fornecedores_por_regiao": chart_fornecedores_por_regiao,
        "chart_cohort_fornecedores": [],
        "ranking_por_receita": ranking_por_receita,
        "ranking_por_qtd_media": ranking_por_qtd_media,
        "ranking_por_ticket_medio": ranking_por_ticket_medio,
        "ranking_por_frequencia": ranking_por_frequencia,
        "ranking_produtos_mais_vendidos": produtos_vendidos_formatted,
    }


@router.get(
    "/fornecedores",
    summary="Métricas agregadas de fornecedores",
    tags=["Fornecedores"],
)
async def get_suppliers(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna métricas agregadas de fornecedores a partir da view ouro (analytics_gold_suppliers).

    Requires client_id for data isolation (RLS).
    """
    return repo.get_gold_suppliers_metrics(client_id)

@router.get(
    "/produtos",
    summary="Métricas agregadas de produtos",
    tags=["Produtos"],
)
async def get_products(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna métricas agregadas de produtos a partir da view ouro (analytics_gold_products).

    Requires client_id for data isolation (RLS).
    """
    return repo.get_gold_products_metrics(client_id)

@router.get(
    "/clientes",
    summary="Métricas agregadas de clientes",
    tags=["Clientes"],
)
async def get_customers(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    """
    Retorna métricas agregadas de clientes a partir da view ouro (analytics_gold_customers).

    Requires client_id for data isolation (RLS).
    """
    return repo.get_gold_customers_metrics(client_id)


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
    - Returns the Supabase user ID as client_id
    """
    # claims.sub = Supabase user ID (external_user_id) = client_id
    if not claims.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado."
        )

    # Ensure clientes_vizu record exists for this user
    # This allows the rest of the system (atendente_core) to use the full auth flow
    try:
        repo.ensure_cliente_vizu_exists(
            external_user_id=claims.sub,
            email=claims.email,
            client_id=claims.sub  # Use Supabase user ID as client_id
        )
    except Exception as e:
        # Log but don't fail - we can still return the ID even if DB write fails
        import logging
        logging.error(f"Failed to create clientes_vizu record: {e}")

    return MeResponse(client_id=claims.sub)
