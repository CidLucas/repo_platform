# services/analytics_api/src/analytics_api/api/endpoints/rankings.py
from datetime import UTC, datetime
from datetime import timezone as tz
from urllib.parse import unquote

from analytics_api.api.dependencies import get_client_id, get_postgres_repository
from analytics_api.api.helpers import dict_to_ranking_item
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.schemas.metrics import (
    CadastralData,
    ChartDataPoint,
    ClienteDetailResponse,
    ClientesOverviewResponse,
    FornecedorDetailResponse,
    FornecedoresOverviewResponse,
    PedidoItem,
    PedidosOverviewResponse,
    ProdutoDetailResponse,
    ProdutoRankingReceita,
    ProdutoRankingTicket,
    ProdutoRankingVolume,
    ProdutosOverviewResponse,
    RankingItem,
)
from fastapi import APIRouter, Depends, HTTPException, Query

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
    period: str = Query("all", description="Período de filtro: week, month, quarter, year, all"),
):
    """Retorna KPIs, rankings e gráficos para a página de Fornecedores a partir da camada ouro."""

    suppliers = repo.get_dim_suppliers(client_id, period) or []
    products = repo.get_dim_products(client_id) or []

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
    time_data = repo.get_v2_time_series(client_id, 'fornecedores_no_tempo')
    # Calculate cumulative sum for frontend (expects total_cumulativo)
    cumulative_sum = 0
    chart_fornecedores_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_fornecedores_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    regional_data = repo.get_v2_regional(client_id, 'fornecedores_por_regiao')
    chart_fornecedores_por_regiao = [
        ChartDataPoint(name=point['name'], total=point['total'], percentual=point['percentual'])
        for point in regional_data
    ]

    # Calculate growth percentage from time series data
    crescimento_percentual = repo.calculate_growth_from_time_series(client_id, 'fornecedores_no_tempo')

    # NEW: Get time-series for receita, ticket medio, quantidade
    receita_time_data = repo.get_v2_time_series(client_id, 'receita_fornecedores_no_tempo')
    chart_receita_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in receita_time_data
    ]

    ticket_time_data = repo.get_v2_time_series(client_id, 'ticket_medio_fornecedores_no_tempo')
    chart_ticketmedio_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in ticket_time_data
    ]

    quantidade_time_data = repo.get_v2_time_series(client_id, 'quantidade_fornecedores_no_tempo')
    chart_quantidade_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in quantidade_time_data
    ]

    return FornecedoresOverviewResponse(
        scorecard_total_fornecedores=len(suppliers),
        scorecard_crescimento_percentual=crescimento_percentual,
        chart_fornecedores_no_tempo=chart_fornecedores_no_tempo,
        chart_receita_no_tempo=chart_receita_no_tempo,
        chart_ticketmedio_no_tempo=chart_ticketmedio_no_tempo,
        chart_quantidade_no_tempo=chart_quantidade_no_tempo,
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
    period: str = Query("all", description="Período de filtro: week, month, quarter, year, all"),
):
    """Retorna KPIs, rankings e gráficos para a página de Clientes a partir da camada ouro."""

    customers = repo.get_dim_customers(client_id, period) or []

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
    regional_data = repo.get_v2_regional(client_id, 'clientes_por_regiao')
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
    time_data = repo.get_v2_time_series(client_id, 'clientes_no_tempo')
    cumulative_sum = 0
    chart_clientes_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_clientes_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    # Calculate growth percentage from time series data
    crescimento_percentual = repo.calculate_growth_from_time_series(client_id, 'clientes_no_tempo')

    # NEW: Get time-series for receita, ticket medio, quantidade from clientes
    receita_time_data = repo.get_v2_time_series(client_id, 'receita_clientes_no_tempo')
    chart_receita_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in receita_time_data
    ]

    ticket_time_data = repo.get_v2_time_series(client_id, 'ticket_medio_clientes_no_tempo')
    chart_ticketmedio_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in ticket_time_data
    ]

    quantidade_time_data = repo.get_v2_time_series(client_id, 'quantidade_clientes_no_tempo')
    chart_quantidade_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in quantidade_time_data
    ]

    return ClientesOverviewResponse(
        scorecard_total_clientes=len(customers),
        scorecard_ticket_medio_geral=float(ticket_medio_geral),
        scorecard_frequencia_media_geral=float(freq_media_geral),
        scorecard_crescimento_percentual=crescimento_percentual,
        chart_clientes_no_tempo=chart_clientes_no_tempo,
        chart_receita_no_tempo=chart_receita_no_tempo,
        chart_ticketmedio_no_tempo=chart_ticketmedio_no_tempo,
        chart_quantidade_no_tempo=chart_quantidade_no_tempo,
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
    period: str = Query("all", description="Período de filtro: week, month, quarter, year, all"),
):
    """Retorna KPIs e rankings para a página de Produtos a partir da camada ouro."""

    products = repo.get_dim_products(client_id, period) or []

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
    time_data = repo.get_v2_time_series(client_id, 'produtos_no_tempo')
    cumulative_sum = 0
    chart_produtos_no_tempo = []
    for point in time_data:
        cumulative_sum += point['total']
        chart_produtos_no_tempo.append(
            ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
        )

    # NEW: Get time-series for receita and quantidade from produtos
    receita_time_data = repo.get_v2_time_series(client_id, 'receita_produtos_no_tempo')
    chart_receita_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in receita_time_data
    ]

    quantidade_time_data = repo.get_v2_time_series(client_id, 'quantidade_produtos_no_tempo')
    chart_quantidade_no_tempo = [
        ChartDataPoint(name=point['name'], total=point['total'])
        for point in quantidade_time_data
    ]

    return ProdutosOverviewResponse(
        scorecard_total_itens_unicos=len(products),
        chart_produtos_no_tempo=chart_produtos_no_tempo,
        chart_receita_no_tempo=chart_receita_no_tempo,
        chart_quantidade_no_tempo=chart_quantidade_no_tempo,
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

    orders = repo.get_fact_sales_aggregated(client_id) or {}

    scorecard_ticket_medio_por_pedido = float(orders.get("avg_order_value", 0))
    scorecard_qtd_media_produtos_por_pedido = float(orders.get("qtd_media_por_pedido", 0))
    scorecard_taxa_recorrencia_clientes_perc = float(orders.get("taxa_recorrencia", 0))
    scorecard_recencia_media_entre_pedidos_dias = float(orders.get("recencia_dias", 0))

    # Regional and last orders from Gold (precomputed)
    regional_data = repo.get_v2_regional(client_id, 'pedidos_por_regiao')
    ranking_pedidos_por_regiao = [
        ChartDataPoint(name=point['name'], contagem=point['contagem'], percentual=point['percentual'])
        for point in regional_data
    ]

    last_orders_data = repo.get_v2_last_orders(client_id, limit=20)
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
    time_data = repo.get_v2_time_series(client_id, 'pedidos_no_tempo')
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

# --- GOLD-BASED DETAIL ENDPOINTS (Level 3) ---
# These read ONLY from gold tables - NO silver/BigQuery queries

@router.get(
    "/cliente/{nome_cliente}/gold",
    response_model=ClienteDetailResponse,
    summary="Detalhe do Cliente (Gold - Leitura Rápida)",
    tags=["Nível 3 - Detalhe", "Ouro"]
)
def get_cliente_detail_gold(
    nome_cliente: str,
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
) -> ClienteDetailResponse:
    """
    Retorna detalhes de um cliente específico lendo APENAS da tabela gold.
    Muito mais rápido que o endpoint /cliente/{nome} que lê do BigQuery.

    Retorna estrutura ClienteDetailResponse:
    - dados_cadastrais: Dados cadastrais do cliente
    - scorecards: Métricas do cliente (receita, ticket médio, frequência, etc)
    - rankings_internos: Rankings internos (mix de produtos por receita)
    """
    nome_decoded = unquote(nome_cliente)

    customers = repo.get_dim_customers(client_id, period="all") or []

    # Filter customers by name - may return multiple records
    matching_customers = [c for c in customers if c.get("customer_name") == nome_decoded]

    if not matching_customers:
        raise HTTPException(status_code=404, detail=f"Cliente '{nome_decoded}' não encontrado")

    # Prioritize records with most complete contact data
    # Score each record: +1 for each non-null contact field
    def score_completeness(cust: dict) -> int:
        score = 0
        if cust.get("telefone"):
            score += 3  # Phone is most important
        if cust.get("customer_cpf_cnpj"):
            score += 2  # CPF/CNPJ is second priority
        if cust.get("endereco_cidade"):
            score += 1
        if cust.get("endereco_uf"):
            score += 1
        if cust.get("endereco_rua"):
            score += 1
        if cust.get("endereco_cep"):
            score += 1
        return score

    # Sort by completeness score (desc) and pick the best record
    customer = max(matching_customers, key=score_completeness)

    # Parse dates
    primeira_venda = customer.get("primeira_venda")
    ultima_venda = customer.get("ultima_venda")
    if isinstance(primeira_venda, str):
        primeira_venda = datetime.fromisoformat(primeira_venda.replace('Z', '+00:00'))
    if isinstance(ultima_venda, str):
        ultima_venda = datetime.fromisoformat(ultima_venda.replace('Z', '+00:00'))

    # Default dates if not available
    now = datetime.now(UTC)
    primeira_venda = primeira_venda or now
    ultima_venda = ultima_venda or now

    # Get top products for this customer from the gold table (pre-aggregated during ETL)
    customer_cpf_cnpj = customer.get("customer_cpf_cnpj")
    mix_de_produtos = []
    if customer_cpf_cnpj:
        products = repo.get_v2_customer_products(client_id, customer_cpf_cnpj, limit=10)
        mix_de_produtos = [
            RankingItem(
                nome=p.get("nome", ""),
                receita_total=float(p.get("receita_total", 0)),
                quantidade_total=float(p.get("quantidade_total", 0)),
                num_pedidos_unicos=int(p.get("num_pedidos", 0)),
                primeira_venda=p.get("primeira_compra") or now,
                ultima_venda=p.get("ultima_compra") or now,
                ticket_medio=0.0,
                qtd_media_por_pedido=0.0,
                frequencia_pedidos_mes=0.0,
                recencia_dias=0,
                valor_unitario_medio=float(p.get("valor_unitario_medio", 0)),
                cluster_score=0.0,
                cluster_tier="",
            )
            for p in products
        ]

    return ClienteDetailResponse(
        dados_cadastrais=CadastralData(
            receiver_nome=customer.get("customer_name", ""),
            receiver_cnpj=customer.get("customer_cpf_cnpj", ""),
            receiver_telefone=customer.get("telefone"),
            receiver_estado=customer.get("endereco_uf"),
            receiver_cidade=customer.get("endereco_cidade"),
        ),
        scorecards=RankingItem(
            nome=customer.get("customer_name", ""),
            receita_total=float(customer.get("lifetime_value", 0)),
            quantidade_total=float(customer.get("quantidade_total", 0)),
            num_pedidos_unicos=int(customer.get("total_orders", customer.get("num_pedidos_unicos", 0))),
            primeira_venda=primeira_venda,
            ultima_venda=ultima_venda,
            ticket_medio=float(customer.get("ticket_medio", customer.get("avg_order_value", 0))),
            qtd_media_por_pedido=float(customer.get("qtd_media_por_pedido", 0)),
            frequencia_pedidos_mes=float(customer.get("frequencia_pedidos_mes", 0)),
            recencia_dias=int(customer.get("recencia_dias", 0)),
            valor_unitario_medio=0.0,
            cluster_score=0.0,
            cluster_tier=customer.get("cluster_tier", ""),
        ),
        rankings_internos={
            "mix_de_produtos_por_receita": mix_de_produtos,
        }
    )


@router.get(
    "/fornecedor/{nome_fornecedor}/gold",
    response_model=FornecedorDetailResponse,
    summary="Detalhe do Fornecedor (Gold - Leitura Rápida)",
    tags=["Nível 3 - Detalhe", "Ouro"]
)
def get_fornecedor_detail_gold(
    nome_fornecedor: str,
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
) -> FornecedorDetailResponse:
    """
    Retorna detalhes de um fornecedor específico lendo APENAS da tabela gold.
    Muito mais rápido que o endpoint /fornecedor/{nome} que lê do BigQuery.
    """
    nome_decoded = unquote(nome_fornecedor)

    suppliers = repo.get_dim_suppliers(client_id, period="all") or []

    # Filter suppliers by name - may return multiple records
    matching_suppliers = [s for s in suppliers if s.get("supplier_name") == nome_decoded]

    if not matching_suppliers:
        raise HTTPException(status_code=404, detail=f"Fornecedor '{nome_decoded}' não encontrado")

    # Prioritize records with most complete contact data
    def score_supplier_completeness(supp: dict) -> int:
        score = 0
        if supp.get("telefone"):
            score += 3
        if supp.get("supplier_cnpj"):
            score += 2
        if supp.get("endereco_cidade"):
            score += 1
        if supp.get("endereco_uf"):
            score += 1
        if supp.get("endereco_rua"):
            score += 1
        return score

    supplier = max(matching_suppliers, key=score_supplier_completeness)

    return FornecedorDetailResponse(
        dados_cadastrais=CadastralData(
            emitter_nome=supplier.get("supplier_name", ""),
            emitter_cnpj=supplier.get("supplier_cnpj", ""),
            emitter_telefone=supplier.get("telefone"),
            emitter_estado=supplier.get("endereco_uf"),
            emitter_cidade=supplier.get("endereco_cidade"),
        ),
        rankings_internos={
            "clientes_por_receita": [],
            "produtos_por_receita": [],
            "regioes_por_receita": [],
        }
    )


@router.get(
    "/produto/{nome_produto}/gold",
    response_model=ProdutoDetailResponse,
    summary="Detalhe do Produto (Gold - Leitura Rápida)",
    tags=["Nível 3 - Detalhe", "Ouro"]
)
def get_produto_detail_gold(
    nome_produto: str,
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
) -> ProdutoDetailResponse:
    """
    Retorna detalhes de um produto específico lendo APENAS da tabela gold.
    Muito mais rápido que o endpoint /produto/{nome} que lê do BigQuery.
    """
    nome_decoded = unquote(nome_produto)

    products = repo.get_dim_products(client_id) or []

    # Filter products by name - may return multiple records
    matching_products = [p for p in products if p.get("product_name") == nome_decoded]

    if not matching_products:
        raise HTTPException(status_code=404, detail=f"Produto '{nome_decoded}' não encontrado")

    # Prioritize records with most recent data and highest metrics
    def score_product_completeness(prod: dict) -> tuple:
        # Return tuple: (has dates, total revenue) for sorting
        has_dates = 1 if prod.get("ultima_venda") else 0
        revenue = float(prod.get("total_revenue", 0))
        return (has_dates, revenue)

    product = max(matching_products, key=score_product_completeness)

    # Parse dates
    primeira_venda = product.get("primeira_venda")
    ultima_venda = product.get("ultima_venda")
    if isinstance(primeira_venda, str):
        primeira_venda = datetime.fromisoformat(primeira_venda.replace('Z', '+00:00'))
    if isinstance(ultima_venda, str):
        ultima_venda = datetime.fromisoformat(ultima_venda.replace('Z', '+00:00'))

    now = datetime.now(UTC)
    primeira_venda = primeira_venda or now
    ultima_venda = ultima_venda or now

    return ProdutoDetailResponse(
        nome_produto=product.get("product_name", ""),
        scorecards=RankingItem(
            nome=product.get("product_name", ""),
            receita_total=float(product.get("total_revenue", 0)),
            quantidade_total=float(product.get("total_quantity", product.get("quantidade_total", 0))),
            num_pedidos_unicos=int(product.get("num_pedidos_unicos", product.get("order_count", 0))),
            primeira_venda=primeira_venda,
            ultima_venda=ultima_venda,
            ticket_medio=float(product.get("ticket_medio", 0)),
            qtd_media_por_pedido=float(product.get("qtd_media_por_pedido", 0)),
            frequencia_pedidos_mes=float(product.get("frequencia_pedidos_mes", 0)),
            recencia_dias=int(product.get("recencia_dias", 0)),
            valor_unitario_medio=float(product.get("avg_price", product.get("valor_unitario_medio", 0))),
            cluster_score=0.0,
            cluster_tier=product.get("cluster_tier", ""),
        ),
        charts={
            "segmentos_de_clientes": [],
        },
        rankings_internos={
            "clientes_por_receita": [],
            "regioes_por_receita": [],
        }
    )


# --- FILTER ENDPOINTS: Customer-Product Cross Analysis ---

@router.get(
    "/filters/products",
    summary="Lista de Produtos para Filtro",
    tags=["Filtros"]
)
def get_products_for_filter(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
) -> list[dict]:
    """
    Retorna lista de produtos distintos para popular dropdown de filtro.
    Inclui nome do produto, receita total e número de clientes.
    """
    return repo.get_distinct_products(client_id)


@router.get(
    "/filters/customers",
    summary="Lista de Clientes para Filtro",
    tags=["Filtros"]
)
def get_customers_for_filter(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
) -> list[dict]:
    """
    Retorna lista de clientes distintos para popular dropdown de filtro.
    Inclui nome do cliente, receita total e número de produtos.
    """
    return repo.get_distinct_customers(client_id)


@router.get(
    "/customers-by-product/{product_name}",
    summary="Clientes que Compraram um Produto",
    tags=["Filtros", "Análise Cruzada"]
)
def get_customers_by_product(
    product_name: str,
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
    limit: int = Query(100, description="Número máximo de clientes"),
) -> list[dict]:
    """
    Retorna clientes que compraram um produto específico.

    Para cada cliente retorna:
    - nome: Nome do cliente
    - customer_cpf_cnpj: CPF/CNPJ do cliente
    - produto_receita: Quanto gastou neste produto
    - produto_quantidade: Quantidade comprada deste produto
    - produto_pedidos: Número de pedidos com este produto
    - cliente_receita_total: Gasto total do cliente (todos produtos)
    - percentual_do_total: % do gasto total que foi neste produto
    """
    nome_decoded = unquote(product_name)
    return repo.get_customers_by_product(client_id, nome_decoded, limit)


@router.get(
    "/products-by-customer/{customer_cpf_cnpj}",
    summary="Produtos Comprados por um Cliente",
    tags=["Filtros", "Análise Cruzada"]
)
def get_products_by_customer(
    customer_cpf_cnpj: str,
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
    limit: int = Query(100, description="Número máximo de produtos"),
) -> list[dict]:
    """
    Retorna produtos comprados por um cliente específico.

    Para cada produto retorna:
    - nome: Nome do produto
    - receita_total: Quanto o cliente gastou neste produto
    - quantidade_total: Quantidade comprada
    - num_pedidos: Número de pedidos
    - valor_unitario_medio: Preço médio unitário
    """
    cpf_decoded = unquote(customer_cpf_cnpj)
    return repo.get_v2_customer_products(client_id, cpf_decoded, limit)


@router.get(
    "/customer-monthly-orders/{customer_cpf_cnpj}",
    summary="Pedidos Mensais de um Cliente",
    tags=["Filtros", "Time Series"]
)
def get_customer_monthly_orders(
    customer_cpf_cnpj: str,
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id),
) -> list[dict]:
    """
    Retorna série temporal de pedidos mensais para um cliente específico.

    Para cada mês retorna:
    - month: Mês no formato YYYY-MM
    - num_pedidos: Número de pedidos únicos naquele mês
    """
    cpf_decoded = unquote(customer_cpf_cnpj)
    return repo.get_customer_monthly_orders(client_id, cpf_decoded)
