# Analytics API Endpoints - Pydantic Objects Reference

This document lists all Pydantic objects used across the Analytics API endpoints.

## Overview

All endpoints now use Pydantic models exclusively - **no raw dicts are returned**.

## Endpoint Files

- **dashboard.py** - Home dashboard metrics
- **rankings.py** - Module-level overviews (Level 2)
- **deep_dive.py** - Detailed views (Level 3)
- **indicators.py** - Cached indicators with comparisons

---

## Pydantic Models by Category

### Core Data Models

#### `ChartDataPoint`
Generic data point for charts (Recharts compatible).
- **Fields:** `name: str` + any additional fields (extra='allow')
- **Used in:** All chart responses across endpoints
- **Example:** `{"name": "2025-01", "total": 150, "percentual": 25.5}`

#### `ChartData`
Complete chart structure with metadata.
- **Fields:** `id: str`, `title: str`, `data: list[ChartDataPoint]`
- **Used in:** HomeMetricsResponse

#### `RankingItem`
Universal ranking model for customers, suppliers, products.
- **Fields:**
  - `nome: str`
  - `receita_total: float`
  - `quantidade_total: float`
  - `num_pedidos_unicos: int`
  - `primeira_venda: datetime`
  - `ultima_venda: datetime`
  - `ticket_medio: float`
  - `qtd_media_por_pedido: float`
  - `frequencia_pedidos_mes: float`
  - `recencia_dias: int`
  - `valor_unitario_medio: float`
  - `cluster_score: float` (0-100 RFM score)
  - `cluster_tier: str` (A/B/C/D segment)
- **Used in:** All ranking endpoints
- **Created by:** `dict_to_ranking_item()` helper function

#### `CadastralData`
Cadastral/dimensional data from silver layer.
- **Fields:** Emitter and receiver contact information
  - `emitter_nome, emitter_cnpj, emitter_telefone, emitter_estado, emitter_cidade`
  - `receiver_nome, receiver_cnpj, receiver_telefone, receiver_estado, receiver_cidade`
- **Used in:** Detail responses (Level 3)

### Product-Specific Rankings

#### `ProdutoRankingReceita`
Simplified product ranking by revenue.
- **Fields:** `nome: str`, `receita_total: float`, `valor_unitario_medio: float`
- **Used in:** Products overview, supplier overview

#### `ProdutoRankingVolume`
Product ranking by volume sold.
- **Fields:** `nome: str`, `quantidade_total: float`, `valor_unitario_medio: float`
- **Used in:** Products overview

#### `ProdutoRankingTicket`
Product ranking by average ticket.
- **Fields:** `nome: str`, `ticket_medio: float`, `valor_unitario_medio: float`
- **Used in:** Products overview

---

## Level 1: Home Dashboard

### `HomeScorecards`
Aggregated KPIs for homepage.
- **Fields:**
  - `receita_total: float`
  - `total_fornecedores: int`
  - `total_produtos: int`
  - `total_regioes: int`
  - `total_clientes: int`
  - `total_pedidos: int`

### `HomeMetricsResponse`
Complete home page response.
- **Fields:** `scorecards: HomeScorecards`, `charts: list[ChartData]`
- **Endpoints:**
  - `GET /dashboard/home`
  - `GET /dashboard/home_gold`

---

## Level 2: Module Overviews

### `FornecedoresOverviewResponse`
Suppliers module overview.
- **Fields:**
  - `scorecard_total_fornecedores: int`
  - `scorecard_crescimento_percentual: float | None`
  - `chart_fornecedores_no_tempo: list[ChartDataPoint]`
  - `chart_fornecedores_por_regiao: list[ChartDataPoint]`
  - `chart_cohort_fornecedores: list[ChartDataPoint]`
  - `ranking_por_receita: list[RankingItem]`
  - `ranking_por_qtd_media: list[RankingItem]`
  - `ranking_por_ticket_medio: list[RankingItem]`
  - `ranking_por_frequencia: list[RankingItem]`
  - `ranking_produtos_mais_vendidos: list[ProdutoRankingReceita]`
- **Endpoints:** `GET /api/fornecedores`

### `ClientesOverviewResponse`
Customers module overview.
- **Fields:**
  - `scorecard_total_clientes: int`
  - `scorecard_ticket_medio_geral: float`
  - `scorecard_frequencia_media_geral: float`
  - `scorecard_crescimento_percentual: float | None`
  - `chart_clientes_por_regiao: list[ChartDataPoint]`
  - `chart_cohort_clientes: list[ChartDataPoint]`
  - `ranking_por_receita: list[RankingItem]`
  - `ranking_por_ticket_medio: list[RankingItem]`
  - `ranking_por_qtd_pedidos: list[RankingItem]`
  - `ranking_por_cluster_vizu: list[RankingItem]`
- **Endpoints:** `GET /api/clientes`

### `ProdutosOverviewResponse`
Products module overview.
- **Fields:**
  - `scorecard_total_itens_unicos: int`
  - `ranking_por_receita: list[ProdutoRankingReceita]`
  - `ranking_por_volume: list[ProdutoRankingVolume]`
  - `ranking_por_ticket_medio: list[ProdutoRankingTicket]`
- **Endpoints:**
  - `GET /api/produtos`
  - `GET /dashboard/produtos/gold`

### `PedidosOverviewResponse`
Orders module overview.
- **Fields:**
  - `scorecard_ticket_medio_por_pedido: float`
  - `scorecard_qtd_media_produtos_por_pedido: float`
  - `scorecard_taxa_recorrencia_clientes_perc: float`
  - `scorecard_recencia_media_entre_pedidos_dias: float`
  - `ranking_pedidos_por_regiao: list[ChartDataPoint]`
  - `ultimos_pedidos: list[PedidoItem]`
- **Endpoints:** `GET /api/pedidos`

#### `PedidoItem`
Single order summary for listings.
- **Fields:**
  - `order_id: str`
  - `data_transacao: datetime`
  - `id_cliente: str`
  - `ticket_pedido: float`
  - `qtd_produtos: int`

---

## Level 3: Detail Views

### `FornecedorDetailResponse`
Supplier detail page.
- **Fields:**
  - `dados_cadastrais: CadastralData`
  - `rankings_internos: dict[str, list[RankingItem]]`
- **Endpoints:** `GET /api/deep-dive/fornecedor/{nome_fornecedor}`

### `ClienteDetailResponse`
Customer detail page.
- **Fields:**
  - `dados_cadastrais: CadastralData`
  - `scorecards: RankingItem | None`
  - `rankings_internos: dict[str, list[RankingItem]]`
- **Endpoints:** `GET /api/deep-dive/cliente/{nome_cliente}`

### `ProdutoDetailResponse`
Product detail page.
- **Fields:**
  - `nome_produto: str`
  - `scorecards: RankingItem | None`
  - `charts: dict[str, list[ChartDataPoint]]`
  - `rankings_internos: dict[str, list[RankingItem]]`
- **Endpoints:** `GET /api/deep-dive/produto/{nome_produto}`

### `PedidoDetailResponse`
Order detail page.
- **Fields:**
  - `order_id: str`
  - `status_pedido: str`
  - `total_pedido: float`
  - `dados_cliente: CadastralData`
  - `itens_pedido: list[PedidoItemDetalhe]`
- **Endpoints:** `GET /api/deep-dive/pedido/{order_id}`

#### `PedidoItemDetalhe`
Line item detail for order.
- **Fields:**
  - `raw_product_description: str`
  - `quantidade: float`
  - `valor_unitario: float`
  - `valor_total_emitter: float`

---

## Indicators Module

### Request/Response Models

#### `IndicatorsRequest`
Request body for fetching indicators.
- **Fields:**
  - `period: PeriodType` (today, yesterday, week, month, quarter, year)
  - `metrics: list[str] | None` (orders, products, customers)
  - `include_comparisons: bool` (default True)

#### `ComparisonData`
Percentage comparison vs previous periods.
- **Fields:**
  - `vs_7_days: float | None`
  - `vs_30_days: float | None`
  - `vs_90_days: float | None`
  - `trend: str | None` (up, down, stable)

#### `OrderMetricsResponse`
Order indicators with comparisons.
- **Fields:**
  - `total: int`
  - `revenue: float`
  - `avg_order_value: float`
  - `growth_rate: float | None`
  - `by_status: dict`
  - `period: str`
  - `comparisons: ComparisonData | None`

#### `ProductMetricsResponse`
Product indicators with comparisons.
- **Fields:**
  - `total_sold: int`
  - `unique_products: int`
  - `top_sellers: list`
  - `low_stock_alerts: int`
  - `avg_price: float`
  - `period: str`
  - `comparisons: ComparisonData | None`

#### `CustomerMetricsResponse`
Customer indicators with comparisons.
- **Fields:**
  - `total_active: int`
  - `new_customers: int`
  - `returning_customers: int`
  - `avg_lifetime_value: float`
  - `period: str`
  - `comparisons: ComparisonData | None`

#### `IndicatorsResponse`
Consolidated indicators response.
- **Fields:**
  - `orders: OrderMetricsResponse | None`
  - `products: ProductMetricsResponse | None`
  - `customers: CustomerMetricsResponse | None`
  - `cached: bool`
  - `generated_at: str`
  - `ttl: int | None`

---

## Helper Functions

### `dict_to_ranking_item(row: dict) -> RankingItem`
Located in: `analytics_api.api.helpers`

Converts dict from gold tables to RankingItem Pydantic model.
- Handles backward compatibility (old vs new column names)
- Provides safe defaults for missing fields
- Used by: rankings.py endpoints

---

## Removed/Deprecated

The following endpoints were **removed** as they returned raw dicts:
- ❌ `GET /dashboard/clientes/gold` (use `/api/clientes`)
- ❌ `GET /dashboard/fornecedores/gold` (use `/api/fornecedores`)
- ❌ `GET /dashboard/fornecedores` (use `/api/fornecedores`)
- ❌ `GET /dashboard/produtos` (use `/api/produtos`)
- ❌ `GET /dashboard/clientes` (use `/api/clientes`)

---

## Summary

### Total Pydantic Models: 22

**Core Models (4):**
- ChartDataPoint
- ChartData
- RankingItem
- CadastralData

**Product Rankings (3):**
- ProdutoRankingReceita
- ProdutoRankingVolume
- ProdutoRankingTicket

**Level 1 - Home (2):**
- HomeScorecards
- HomeMetricsResponse

**Level 2 - Modules (5):**
- FornecedoresOverviewResponse
- ClientesOverviewResponse
- ProdutosOverviewResponse
- PedidosOverviewResponse
- PedidoItem

**Level 3 - Details (5):**
- FornecedorDetailResponse
- ClienteDetailResponse
- ProdutoDetailResponse
- PedidoDetailResponse
- PedidoItemDetalhe

**Indicators (7):**
- IndicatorsRequest
- ComparisonData
- OrderMetricsResponse
- ProductMetricsResponse
- CustomerMetricsResponse
- IndicatorsResponse
- MeResponse (dashboard.py)

### Type Safety

All endpoints now:
✅ Return typed Pydantic models (no raw dicts)
✅ Have proper request/response schemas
✅ Support automatic OpenAPI documentation
✅ Enable client code generation
✅ Provide runtime validation
