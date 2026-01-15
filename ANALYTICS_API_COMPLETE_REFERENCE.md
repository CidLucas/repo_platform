# Analytics API - Complete Reference Documentation

**Generated:** 2026-01-15
**API Version:** Current
**Base URL:** `/api/`

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [All Endpoints Summary](#all-endpoints-summary)
4. [Response Object Definitions](#response-object-definitions)
5. [Canonical Silver Layer Views](#canonical-silver-layer-views)
6. [Data Type Reference](#data-type-reference)
7. [Usage Examples](#usage-examples)

---

## API Overview

The Analytics API provides a comprehensive set of endpoints for business intelligence and analytics. It follows a three-tier architecture:

- **Bronze Layer**: Raw data from client systems (BigQuery, CSV, etc.)
- **Silver Layer**: Canonical business entities (TransacaoView, ClienteView, etc.)
- **Gold Layer**: Pre-computed aggregations, KPIs, and metrics

The API is organized into three hierarchical levels:

1. **Level 1 (Home)**: Aggregated metrics across all modules
2. **Level 2 (Modules)**: Overview pages for Fornecedores, Clientes, Produtos, Pedidos
3. **Level 3 (Detail)**: Individual entity details

---

## Authentication

The API uses **JWT-based authentication** via Supabase with support for **Google OAuth**.

### Client ID Extraction

The `client_id` is extracted from (in order of precedence):
1. Query parameter: `?client_id=xxx`
2. Header: `X-Client-ID: xxx`
3. JWT token `sub` claim (Supabase user ID)

### Authentication Endpoints

#### POST `/api/auth/google/login`
Initiates Google OAuth login flow.

**Response:**
```json
{
  "auth_url": "string"
}
```

#### GET `/api/auth/google/callback`
Google OAuth callback handler.

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string"
}
```

#### GET `/api/dashboard/me`
Returns authenticated user's client_id.

**Response Model:** `MeResponse`
```json
{
  "client_id": "string"
}
```

---

## All Endpoints Summary

### Level 1: Home Dashboard

| Method | Endpoint | Response Model | Description |
|--------|----------|----------------|-------------|
| GET | `/api/dashboard/home` | `HomeMetricsResponse` | Aggregated metrics and charts for home page |
| GET | `/api/dashboard/home_gold` | `HomeMetricsResponse` | Home metrics from gold layer (all tables) |

### Level 2: Module Overview

| Method | Endpoint | Response Model | Description |
|--------|----------|----------------|-------------|
| GET | `/api/fornecedores` | `FornecedoresOverviewResponse` | Suppliers: KPIs, rankings, charts |
| GET | `/api/clientes` | `ClientesOverviewResponse` | Customers: KPIs, rankings, charts |
| GET | `/api/produtos` | `ProdutosOverviewResponse` | Products: KPIs, rankings |
| GET | `/api/pedidos` | `PedidosOverviewResponse` | Orders: KPIs, recent orders, charts |
| GET | `/api/dashboard/produtos/gold` | `ProdutosOverviewResponse` | Products from gold layer |

### Level 3: Detail Pages

| Method | Endpoint | Response Model | Description |
|--------|----------|----------------|-------------|
| GET | `/api/fornecedor/{nome_fornecedor}` | `FornecedorDetailResponse` | Supplier detail: cadastral data, rankings |
| GET | `/api/cliente/{nome_cliente}` | `ClienteDetailResponse` | Customer detail: cadastral data, scorecards, rankings |
| GET | `/api/produto/{nome_produto}` | `ProdutoDetailResponse` | Product detail: scorecards, charts, rankings |
| GET | `/api/pedido/{order_id}` | `PedidoDetailResponse` | Order detail: customer data, line items |

### Indicators Endpoints

| Method | Endpoint | Response Model | Description |
|--------|----------|----------------|-------------|
| POST | `/api/indicators` | `IndicatorsResponse` | Consolidated indicators for period |
| GET | `/api/indicators/orders` | `OrderMetricsResponse` | Orders indicators only |
| GET | `/api/indicators/products` | `ProductMetricsResponse` | Products indicators only |
| GET | `/api/indicators/customers` | `CustomerMetricsResponse` | Customers indicators only |

### Ingestion Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/api/ingest/recompute` | 202 ACCEPTED | Recalculates and persists gold metrics |

**Response:**
```json
{
  "status": "accepted",
  "detail": "Gold metrics recomputed"
}
```

### Deprecated Endpoints

| Method | Endpoint | Status | Replacement |
|--------|----------|--------|-------------|
| GET | `/api/dashboard/clientes/gold` | DEPRECATED | Use `/api/clientes` instead |

---

## Response Object Definitions

### Generic/Reusable Models

#### ChartDataPoint
Generic data point for charts (e.g., Recharts).

**Fields:**
```typescript
{
  name: string;              // X-axis label (e.g., "2025-01", "SP", "Tier 1")
  // Dynamic fields (Config: extra = 'allow'):
  receita?: number;
  contagem?: number;
  percentual?: number;
  total?: number;
  total_cumulativo?: number;
  [key: string]: any;        // Allows any additional metrics
}
```

**Pydantic Definition:**
```python
class ChartDataPoint(BaseModel):
    name: str
    class Config:
        extra = 'allow'  # Allows dynamic Y-axis metrics
```

---

#### ChartData
Complete structure for a chart.

**Fields:**
```typescript
{
  id: string;                // e.g., "receita-por-mes"
  title: string;
  data: ChartDataPoint[];
}
```

---

#### RankingItem
Complete ranking object with 13 fields - the core aggregation model.

**Fields:**
```typescript
{
  nome: string;                      // Dimension name (customer, product, supplier)
  receita_total: number;             // Total revenue
  quantidade_total: number;          // Total quantity sold
  num_pedidos_unicos: number;        // Unique order count
  primeira_venda: string;            // ISO 8601 datetime
  ultima_venda: string;              // ISO 8601 datetime
  ticket_medio: number;              // Average order value
  qtd_media_por_pedido: number;      // Average quantity per order
  frequencia_pedidos_mes: number;    // Order frequency (orders/month)
  recencia_dias: number;             // Days since last order
  valor_unitario_medio: number;      // Average unit price
  cluster_score: number;             // RFM score (0-100)
  cluster_tier: string;              // Segmentation tier (A, B, C, D)
}
```

**Pydantic Definition:**
```python
class RankingItem(BaseModel):
    nome: str = Field(description="Nome da dimensão")
    receita_total: float
    quantidade_total: float
    num_pedidos_unicos: int
    primeira_venda: datetime
    ultima_venda: datetime
    ticket_medio: float
    qtd_media_por_pedido: float
    frequencia_pedidos_mes: float
    recencia_dias: int
    valor_unitario_medio: float
    cluster_score: float = Field(description="Score RFM (0-100)")
    cluster_tier: str = Field(description="Segmento (A, B, C, D)")

    class Config:
        orm_mode = True
```

---

#### CadastralData
Cadastral (registration) data for suppliers or customers.

**Fields:**
```typescript
{
  // Supplier fields (Emitter)
  emitter_nome?: string | null;
  emitter_cnpj?: string | null;
  emitter_telefone?: string | null;
  emitter_estado?: string | null;
  emitter_cidade?: string | null;

  // Customer fields (Receiver)
  receiver_nome?: string | null;
  receiver_cnpj?: string | null;
  receiver_telefone?: string | null;
  receiver_estado?: string | null;
  receiver_cidade?: string | null;
}
```

**Pydantic Definition:**
```python
class CadastralData(BaseModel):
    emitter_nome: str | None = None
    emitter_cnpj: str | None = None
    emitter_telefone: str | None = None
    emitter_estado: str | None = None
    emitter_cidade: str | None = None
    receiver_nome: str | None = None
    receiver_cnpj: str | None = None
    receiver_telefone: str | None = None
    receiver_estado: str | None = None
    receiver_cidade: str | None = None

    class Config:
        extra = 'ignore'
```

---

### Product-Specific Ranking Models

#### ProdutoRankingReceita
Simplified product ranking by revenue.

**Fields:**
```typescript
{
  nome: string;                      // Product name
  receita_total: number;             // Total revenue
  valor_unitario_medio: number;      // Average unit price
}
```

---

#### ProdutoRankingVolume
Simplified product ranking by volume.

**Fields:**
```typescript
{
  nome: string;                      // Product name
  quantidade_total: number;          // Total quantity sold
  valor_unitario_medio: number;      // Average unit price
}
```

---

#### ProdutoRankingTicket
Simplified product ranking by ticket medio.

**Fields:**
```typescript
{
  nome: string;                      // Product name
  ticket_medio: number;              // Average ticket value
  valor_unitario_medio: number;      // Average unit price
}
```

---

### Level 1: Home

#### HomeScorecards
Aggregated scorecards for the home page.

**Fields:**
```typescript
{
  receita_total: number;             // Total revenue
  total_fornecedores: number;        // Total suppliers
  total_produtos: number;            // Total products
  total_regioes: number;             // Total regions
  total_clientes: number;            // Total customers
  total_pedidos: number;             // Total orders
}
```

---

#### HomeMetricsResponse
Complete response for home page.

**Fields:**
```typescript
{
  scorecards: HomeScorecards;
  charts: ChartData[];
}
```

**Endpoint:** `GET /api/dashboard/home`, `GET /api/dashboard/home_gold`

---

### Level 2: Module Overview

#### FornecedoresOverviewResponse
Suppliers overview with KPIs, rankings, and charts.

**Fields:**
```typescript
{
  scorecard_total_fornecedores: number;
  scorecard_crescimento_percentual?: number | null;     // Growth % of supplier base
  chart_fornecedores_no_tempo: ChartDataPoint[];        // Time series
  chart_fornecedores_por_regiao: ChartDataPoint[];      // Regional breakdown
  chart_cohort_fornecedores: ChartDataPoint[];          // Cohort/tier distribution
  ranking_por_receita: RankingItem[];                   // Top 10 by revenue
  ranking_por_qtd_media: RankingItem[];                 // Top 10 by avg quantity
  ranking_por_ticket_medio: RankingItem[];              // Top 10 by avg ticket
  ranking_por_frequencia: RankingItem[];                // Top 10 by frequency
  ranking_produtos_mais_vendidos: ProdutoRankingReceita[]; // Top 10 products
}
```

**Endpoint:** `GET /api/fornecedores`

**Pydantic Definition:**
```python
class FornecedoresOverviewResponse(BaseModel):
    scorecard_total_fornecedores: int
    scorecard_crescimento_percentual: float | None = None
    chart_fornecedores_no_tempo: list[ChartDataPoint]
    chart_fornecedores_por_regiao: list[ChartDataPoint]
    chart_cohort_fornecedores: list[ChartDataPoint]
    ranking_por_receita: list[RankingItem]
    ranking_por_qtd_media: list[RankingItem]
    ranking_por_ticket_medio: list[RankingItem]
    ranking_por_frequencia: list[RankingItem]
    ranking_produtos_mais_vendidos: list[ProdutoRankingReceita]
```

---

#### ClientesOverviewResponse
Customers overview with KPIs, rankings, and charts.

**Fields:**
```typescript
{
  scorecard_total_clientes: number;
  scorecard_ticket_medio_geral: number;                 // Overall average ticket
  scorecard_frequencia_media_geral: number;             // Overall avg frequency
  scorecard_crescimento_percentual?: number | null;     // Growth % of customer base
  chart_clientes_no_tempo: ChartDataPoint[];            // Time series
  chart_clientes_por_regiao: ChartDataPoint[];          // Regional breakdown
  chart_cohort_clientes: ChartDataPoint[];              // Cohort/tier distribution
  ranking_por_receita: RankingItem[];                   // Top 10 by revenue
  ranking_por_ticket_medio: RankingItem[];              // Top 10 by avg ticket
  ranking_por_qtd_pedidos: RankingItem[];               // Top 10 by order count
  ranking_por_cluster_vizu: RankingItem[];              // Top 10 by cluster score
}
```

**Endpoint:** `GET /api/clientes`

**Pydantic Definition:**
```python
class ClientesOverviewResponse(BaseModel):
    scorecard_total_clientes: int
    scorecard_ticket_medio_geral: float
    scorecard_frequencia_media_geral: float
    scorecard_crescimento_percentual: float | None = None
    chart_clientes_no_tempo: list[ChartDataPoint]
    chart_clientes_por_regiao: list[ChartDataPoint]
    chart_cohort_clientes: list[ChartDataPoint]
    ranking_por_receita: list[RankingItem]
    ranking_por_ticket_medio: list[RankingItem]
    ranking_por_qtd_pedidos: list[RankingItem]
    ranking_por_cluster_vizu: list[RankingItem]
```

---

#### ProdutosOverviewResponse
Products overview with KPIs and rankings.

**Fields:**
```typescript
{
  scorecard_total_itens_unicos: number;
  chart_produtos_no_tempo: ChartDataPoint[];            // Time series
  ranking_por_receita: ProdutoRankingReceita[];         // Top 10 by revenue
  ranking_por_volume: ProdutoRankingVolume[];           // Top 10 by volume
  ranking_por_ticket_medio: ProdutoRankingTicket[];     // Top 10 by ticket
}
```

**Endpoint:** `GET /api/produtos`, `GET /api/dashboard/produtos/gold`

**Pydantic Definition:**
```python
class ProdutosOverviewResponse(BaseModel):
    scorecard_total_itens_unicos: int
    chart_produtos_no_tempo: list[ChartDataPoint]
    ranking_por_receita: list[ProdutoRankingReceita]
    ranking_por_volume: list[ProdutoRankingVolume]
    ranking_por_ticket_medio: list[ProdutoRankingTicket]
```

---

#### PedidoItem
Summary information for a single order.

**Fields:**
```typescript
{
  order_id: string;
  data_transacao: string;            // ISO 8601 datetime
  id_cliente: string;
  ticket_pedido: number;
  qtd_produtos: number;
}
```

**Pydantic Definition:**
```python
class PedidoItem(BaseModel):
    order_id: str
    data_transacao: datetime
    id_cliente: str
    ticket_pedido: float
    qtd_produtos: int
```

---

#### PedidosOverviewResponse
Orders overview with KPIs and recent orders.

**Fields:**
```typescript
{
  scorecard_ticket_medio_por_pedido: number;
  scorecard_qtd_media_produtos_por_pedido: number;
  scorecard_taxa_recorrencia_clientes_perc: number;     // Customer recurrence rate %
  scorecard_recencia_media_entre_pedidos_dias: number;  // Avg days between orders
  chart_pedidos_no_tempo: ChartDataPoint[];             // Time series
  ranking_pedidos_por_regiao: ChartDataPoint[];         // Regional breakdown
  ultimos_pedidos: PedidoItem[];                        // Last 20 orders
}
```

**Endpoint:** `GET /api/pedidos`

**Pydantic Definition:**
```python
class PedidosOverviewResponse(BaseModel):
    scorecard_ticket_medio_por_pedido: float
    scorecard_qtd_media_produtos_por_pedido: float
    scorecard_taxa_recorrencia_clientes_perc: float
    scorecard_recencia_media_entre_pedidos_dias: float
    chart_pedidos_no_tempo: list[ChartDataPoint]
    ranking_pedidos_por_regiao: list[ChartDataPoint]
    ultimos_pedidos: list[PedidoItem]
```

---

### Level 3: Detail Pages

#### FornecedorDetailResponse
Supplier detail page.

**Fields:**
```typescript
{
  dados_cadastrais: CadastralData;
  rankings_internos: {
    [key: string]: RankingItem[];    // e.g., "produtos", "clientes", "regioes"
  };
}
```

**Endpoint:** `GET /api/fornecedor/{nome_fornecedor}`

**Pydantic Definition:**
```python
class FornecedorDetailResponse(BaseModel):
    dados_cadastrais: CadastralData
    rankings_internos: dict[str, list[RankingItem]]
```

---

#### ClienteDetailResponse
Customer detail page.

**Fields:**
```typescript
{
  dados_cadastrais: CadastralData;
  scorecards: RankingItem | null;                       // Customer's own metrics
  rankings_internos: {
    [key: string]: RankingItem[];    // e.g., "produtos", "fornecedores"
  };
}
```

**Endpoint:** `GET /api/cliente/{nome_cliente}`

**Pydantic Definition:**
```python
class ClienteDetailResponse(BaseModel):
    dados_cadastrais: CadastralData
    scorecards: RankingItem | None
    rankings_internos: dict[str, list[RankingItem]]
```

---

#### ProdutoDetailResponse
Product detail page.

**Fields:**
```typescript
{
  nome_produto: string;
  scorecards: RankingItem | null;                       // Product's own metrics
  charts: {
    [key: string]: ChartDataPoint[];  // e.g., "vendas_no_tempo"
  };
  rankings_internos: {
    [key: string]: RankingItem[];     // e.g., "clientes", "fornecedores"
  };
}
```

**Endpoint:** `GET /api/produto/{nome_produto}`

**Pydantic Definition:**
```python
class ProdutoDetailResponse(BaseModel):
    nome_produto: str
    scorecards: RankingItem | None
    charts: dict[str, list[ChartDataPoint]]
    rankings_internos: dict[str, list[RankingItem]]
```

---

#### PedidoItemDetalhe
Line item within an order.

**Fields:**
```typescript
{
  raw_product_description: string;
  quantidade: number;
  valor_unitario: number;
  valor_total_emitter: number;
}
```

**Pydantic Definition:**
```python
class PedidoItemDetalhe(BaseModel):
    raw_product_description: str
    quantidade: float
    valor_unitario: float
    valor_total_emitter: float
```

---

#### PedidoDetailResponse
Order detail page.

**Fields:**
```typescript
{
  order_id: string;
  status_pedido: string;
  total_pedido: number;
  dados_cliente: CadastralData;
  itens_pedido: PedidoItemDetalhe[];
}
```

**Endpoint:** `GET /api/pedido/{order_id}`

**Pydantic Definition:**
```python
class PedidoDetailResponse(BaseModel):
    order_id: str
    status_pedido: str
    total_pedido: float
    dados_cliente: CadastralData
    itens_pedido: list[PedidoItemDetalhe]
```

---

### Indicators Endpoints

#### ComparisonData
Period comparison metrics.

**Fields:**
```typescript
{
  vs_7_days?: number | null;         // % variation vs 7-day average
  vs_30_days?: number | null;        // % variation vs 30-day average
  vs_90_days?: number | null;        // % variation vs 90-day average
  trend?: string | null;             // "up", "down", "stable"
}
```

**Pydantic Definition:**
```python
class ComparisonData(BaseModel):
    vs_7_days: float | None = Field(None, description="% variação vs média 7 dias")
    vs_30_days: float | None = Field(None, description="% variação vs média 30 dias")
    vs_90_days: float | None = Field(None, description="% variação vs média 90 dias")
    trend: str | None = Field(None, description="Tendência: up, down, stable")
```

---

#### IndicatorsRequest
Request body for indicators endpoint.

**Fields:**
```typescript
{
  period: "today" | "yesterday" | "week" | "month" | "quarter" | "year";
  metrics?: string[] | null;         // ["orders", "products", "customers"]
  include_comparisons: boolean;      // Default: true
}
```

**Pydantic Definition:**
```python
class IndicatorsRequest(BaseModel):
    period: PeriodType = "today"
    metrics: list[str] | None = None
    include_comparisons: bool = Field(True, description="Incluir comparativos")
```

**PeriodType Options:**
- `today`: Current day
- `yesterday`: Previous day
- `week`: Last 7 days
- `month`: Last 30 days
- `quarter`: Last 90 days
- `year`: Last 365 days

---

#### OrderMetricsResponse
Order metrics with comparisons.

**Fields:**
```typescript
{
  total: number;
  revenue: number;
  avg_order_value: number;
  growth_rate: number | null;
  by_status: Record<string, any>;
  period: string;
  comparisons?: ComparisonData | null;
}
```

**Endpoint:** `GET /api/indicators/orders`

**Pydantic Definition:**
```python
class OrderMetricsResponse(BaseModel):
    total: int
    revenue: float
    avg_order_value: float
    growth_rate: float | None
    by_status: dict
    period: str
    comparisons: ComparisonData | None = None
```

---

#### ProductMetricsResponse
Product metrics with comparisons.

**Fields:**
```typescript
{
  total_sold: number;
  unique_products: number;
  top_sellers: any[];
  low_stock_alerts: number;
  avg_price: number;
  period: string;
  comparisons?: ComparisonData | null;
}
```

**Endpoint:** `GET /api/indicators/products`

**Pydantic Definition:**
```python
class ProductMetricsResponse(BaseModel):
    total_sold: int
    unique_products: int
    top_sellers: list
    low_stock_alerts: int
    avg_price: float
    period: str
    comparisons: ComparisonData | None = None
```

---

#### CustomerMetricsResponse
Customer metrics with comparisons.

**Fields:**
```typescript
{
  total_active: number;
  new_customers: number;
  returning_customers: number;
  avg_lifetime_value: number;
  period: string;
  comparisons?: ComparisonData | null;
}
```

**Endpoint:** `GET /api/indicators/customers`

**Pydantic Definition:**
```python
class CustomerMetricsResponse(BaseModel):
    total_active: int
    new_customers: int
    returning_customers: int
    avg_lifetime_value: float
    period: str
    comparisons: ComparisonData | None = None
```

---

#### IndicatorsResponse
Consolidated indicators response.

**Fields:**
```typescript
{
  orders?: OrderMetricsResponse | null;
  products?: ProductMetricsResponse | null;
  customers?: CustomerMetricsResponse | null;
  cached: boolean;
  generated_at: string;              // ISO 8601 datetime
  ttl?: number | null;               // Cache TTL in seconds
}
```

**Endpoint:** `POST /api/indicators`

**Pydantic Definition:**
```python
class IndicatorsResponse(BaseModel):
    orders: OrderMetricsResponse | None = None
    products: ProductMetricsResponse | None = None
    customers: CustomerMetricsResponse | None = None
    cached: bool
    generated_at: str
    ttl: int | None = None
```

---

## Canonical Silver Layer Views

The Silver Layer defines canonical business entities used for transformations.

### RegiaoView
Geographic dimension representing a location.

**Fields:**
```typescript
{
  id_regiao: string;                 // Unique region ID
  cidade?: string | null;
  estado?: string | null;
  pais?: string | null;
}
```

**Pydantic Definition:**
```python
class RegiaoView(BaseModel):
    id_regiao: str = Field(description="ID único da região")
    cidade: str | None = None
    estado: str | None = None
    pais: str | None = None

    class Config:
        orm_mode = True
        frozen = True  # Dimensions are immutable
```

---

### ClienteView
Customer dimension (the buyer).

**Fields:**
```typescript
{
  id_cliente: string;                // Unique customer ID (CNPJ, email, etc.)
  nome_cliente: string;
  id_regiao: string;                 // Foreign key to RegiaoView
  data_cadastro?: string | null;     // ISO 8601 datetime
}
```

**Pydantic Definition:**
```python
class ClienteView(BaseModel):
    id_cliente: str = Field(description="ID único do cliente")
    nome_cliente: str
    id_regiao: str = Field(description="Chave estrangeira para RegiaoView")
    data_cadastro: datetime | None = None

    class Config:
        orm_mode = True
        frozen = True
```

---

### VendedorView
Seller/supplier dimension.

**Fields:**
```typescript
{
  id_vendedor: string;               // Unique seller ID (CNPJ, etc.)
  nome_vendedor: string;
  id_regiao: string;                 // Foreign key to RegiaoView
}
```

**Pydantic Definition:**
```python
class VendedorView(BaseModel):
    id_vendedor: str = Field(description="ID único do vendedor")
    nome_vendedor: str
    id_regiao: str = Field(description="Chave estrangeira para RegiaoView")

    class Config:
        orm_mode = True
        frozen = True
```

---

### ProdutoView
Product dimension.

**Fields:**
```typescript
{
  id_produto: string;                // Unique product ID (SKU)
  nome_produto: string;
  categoria?: string | null;
  subcategoria?: string | null;
}
```

**Pydantic Definition:**
```python
class ProdutoView(BaseModel):
    id_produto: str = Field(description="ID único do produto (SKU)")
    nome_produto: str
    categoria: str | None = None
    subcategoria: str | None = None

    class Config:
        orm_mode = True
        frozen = True
```

---

### TransacaoView
Transaction fact table (the central event).

**Fields:**
```typescript
{
  id_transacao: string;              // Unique transaction ID
  data_transacao: string;            // ISO 8601 datetime
  id_cliente: string;                // Foreign key to ClienteView
  id_vendedor: string;               // Foreign key to VendedorView
  id_produto: string;                // Foreign key to ProdutoView
  valor_total: number;               // Revenue metric
  quantidade: number;                // Quantity metric
  preco_unitario?: number | null;    // Unit price
}
```

**Pydantic Definition:**
```python
class TransacaoView(BaseModel):
    id_transacao: str = Field(description="ID único do evento")
    data_transacao: datetime
    id_cliente: str = Field(description="Chave para ClienteView")
    id_vendedor: str = Field(description="Chave para VendedorView")
    id_produto: str = Field(description="Chave para ProdutoView")
    valor_total: float = Field(description="Métrica 'receita'")
    quantidade: int = Field(description="Métrica 'quantidade'")
    preco_unitario: float | None = None

    class Config:
        orm_mode = True
```

---

### EstoqueView
Inventory snapshot fact table.

**Fields:**
```typescript
{
  id_produto: string;                // Foreign key to ProdutoView
  id_local_estoque: string;          // Storage location ID
  quantidade_disponivel: number;
  data_snapshot: string;             // ISO 8601 datetime
}
```

**Pydantic Definition:**
```python
class EstoqueView(BaseModel):
    id_produto: str = Field(description="Chave para ProdutoView")
    id_local_estoque: str = Field(description="Onde o estoque está")
    quantidade_disponivel: int
    data_snapshot: datetime

    class Config:
        orm_mode = True
```

---

## Data Type Reference

### Python to TypeScript Type Mapping

| Python Type | TypeScript Type | Notes |
|-------------|-----------------|-------|
| `str` | `string` | |
| `int` | `number` | Integer values |
| `float` | `number` | Decimal values |
| `bool` | `boolean` | |
| `datetime` | `string` | ISO 8601 format |
| `list[T]` | `T[]` | Array of type T |
| `dict[K, V]` | `Record<K, V>` | Object with keys K and values V |
| `T \| None` | `T \| null` | Optional/nullable |
| `Any` | `any` | Untyped |

### Common Datetime Format

All datetime fields are returned as ISO 8601 strings:
```
"2025-01-15T14:30:00Z"
```

### Numeric Precision

- Revenue, prices, amounts: `float` (2 decimal places recommended)
- Counts, quantities: `int` or `float` depending on source
- Percentages: `float` (0-100 scale)

---

## Usage Examples

### Example 1: Get Home Dashboard

**Request:**
```http
GET /api/dashboard/home
X-Client-ID: client_123
```

**Response:**
```json
{
  "scorecards": {
    "receita_total": 1250000.50,
    "total_fornecedores": 45,
    "total_produtos": 320,
    "total_regioes": 8,
    "total_clientes": 156,
    "total_pedidos": 2340
  },
  "charts": [
    {
      "id": "receita-por-mes",
      "title": "Receita Mensal",
      "data": [
        {
          "name": "2025-01",
          "receita": 150000.00
        },
        {
          "name": "2025-02",
          "receita": 175000.00
        }
      ]
    }
  ]
}
```

---

### Example 2: Get Customers Overview

**Request:**
```http
GET /api/clientes
X-Client-ID: client_123
```

**Response:**
```json
{
  "scorecard_total_clientes": 156,
  "scorecard_ticket_medio_geral": 534.23,
  "scorecard_frequencia_media_geral": 2.5,
  "scorecard_crescimento_percentual": 12.5,
  "chart_clientes_no_tempo": [
    {
      "name": "2025-01",
      "total": 120,
      "total_cumulativo": 120
    },
    {
      "name": "2025-02",
      "total": 36,
      "total_cumulativo": 156
    }
  ],
  "chart_clientes_por_regiao": [
    {
      "name": "SP",
      "contagem": 85,
      "percentual": 54.5
    },
    {
      "name": "RJ",
      "contagem": 42,
      "percentual": 26.9
    }
  ],
  "chart_cohort_clientes": [
    {
      "name": "A",
      "contagem": 25,
      "percentual": 16.0
    },
    {
      "name": "B",
      "contagem": 45,
      "percentual": 28.8
    }
  ],
  "ranking_por_receita": [
    {
      "nome": "Cliente XYZ Ltda",
      "receita_total": 125000.00,
      "quantidade_total": 2500.0,
      "num_pedidos_unicos": 45,
      "primeira_venda": "2024-03-15T10:30:00Z",
      "ultima_venda": "2025-01-10T16:45:00Z",
      "ticket_medio": 2777.78,
      "qtd_media_por_pedido": 55.56,
      "frequencia_pedidos_mes": 4.5,
      "recencia_dias": 5,
      "valor_unitario_medio": 50.00,
      "cluster_score": 95.5,
      "cluster_tier": "A"
    }
  ],
  "ranking_por_ticket_medio": [...],
  "ranking_por_qtd_pedidos": [...],
  "ranking_por_cluster_vizu": [...]
}
```

---

### Example 3: Get Customer Detail

**Request:**
```http
GET /api/cliente/Cliente%20XYZ%20Ltda
X-Client-ID: client_123
```

**Response:**
```json
{
  "dados_cadastrais": {
    "receiver_nome": "Cliente XYZ Ltda",
    "receiver_cnpj": "12.345.678/0001-90",
    "receiver_telefone": "+55 11 98765-4321",
    "receiver_estado": "SP",
    "receiver_cidade": "São Paulo",
    "emitter_nome": null,
    "emitter_cnpj": null,
    "emitter_telefone": null,
    "emitter_estado": null,
    "emitter_cidade": null
  },
  "scorecards": {
    "nome": "Cliente XYZ Ltda",
    "receita_total": 125000.00,
    "quantidade_total": 2500.0,
    "num_pedidos_unicos": 45,
    "primeira_venda": "2024-03-15T10:30:00Z",
    "ultima_venda": "2025-01-10T16:45:00Z",
    "ticket_medio": 2777.78,
    "qtd_media_por_pedido": 55.56,
    "frequencia_pedidos_mes": 4.5,
    "recencia_dias": 5,
    "valor_unitario_medio": 50.00,
    "cluster_score": 95.5,
    "cluster_tier": "A"
  },
  "rankings_internos": {
    "produtos": [
      {
        "nome": "Produto A",
        "receita_total": 45000.00,
        ...
      }
    ],
    "fornecedores": [...]
  }
}
```

---

### Example 4: Get Indicators

**Request:**
```http
POST /api/indicators
Content-Type: application/json
X-Client-ID: client_123

{
  "period": "month",
  "metrics": ["orders", "customers"],
  "include_comparisons": true
}
```

**Response:**
```json
{
  "orders": {
    "total": 234,
    "revenue": 125000.50,
    "avg_order_value": 534.19,
    "growth_rate": 12.5,
    "by_status": {
      "completed": 210,
      "pending": 24
    },
    "period": "month",
    "comparisons": {
      "vs_7_days": 8.5,
      "vs_30_days": 12.3,
      "vs_90_days": 15.7,
      "trend": "up"
    }
  },
  "customers": {
    "total_active": 156,
    "new_customers": 24,
    "returning_customers": 132,
    "avg_lifetime_value": 8012.50,
    "period": "month",
    "comparisons": {
      "vs_7_days": 5.2,
      "vs_30_days": 10.8,
      "vs_90_days": 18.3,
      "trend": "up"
    }
  },
  "products": null,
  "cached": true,
  "generated_at": "2025-01-15T14:30:00Z",
  "ttl": 3600
}
```

---

## Key Features & Metadata

### Data Architecture
- **Bronze Layer**: Raw data from client systems
- **Silver Layer**: Canonical business entities (views)
- **Gold Layer**: Pre-computed aggregations and metrics

### Dynamic Fields in ChartDataPoint
The `ChartDataPoint` model uses Pydantic's `extra = 'allow'` config, enabling dynamic Y-axis metrics:
- `receita` - Revenue
- `contagem` - Count
- `percentual` - Percentage
- `total` - Total value
- `total_cumulativo` - Cumulative total
- Any custom metric as needed

### Helper Functions
The API includes a helper function for converting gold table dictionaries to `RankingItem` models:

**Location:** `/services/analytics_api/src/analytics_api/api/helpers.py`

```python
def dict_to_ranking_item(data: dict) -> RankingItem:
    """
    Converts a gold table dictionary to a RankingItem model.
    Maps field names from gold schema to RankingItem schema.
    """
```

### Time Series Calculations
All time series charts include:
- `total`: Period-specific count/value
- `total_cumulativo`: Cumulative sum (calculated on-the-fly)

Growth percentages are calculated by comparing the first and last periods in the time series.

### Ranking Item Field Mapping
Gold table fields map to `RankingItem` as follows:

| Gold Field | RankingItem Field |
|------------|------------------|
| `customer_name` / `supplier_name` / `product_name` | `nome` |
| `lifetime_value` / `total_revenue` | `receita_total` |
| `total_quantity_sold` | `quantidade_total` |
| `total_orders` | `num_pedidos_unicos` |
| `first_order_date` | `primeira_venda` |
| `last_order_date` | `ultima_venda` |
| `avg_order_value` / `ticket_medio` | `ticket_medio` |
| `qtd_media_por_pedido` | `qtd_media_por_pedido` |
| `frequencia_pedidos_mes` | `frequencia_pedidos_mes` |
| `recencia_dias` | `recencia_dias` |
| `avg_price` | `valor_unitario_medio` |
| `cluster_score` | `cluster_score` |
| `cluster_tier` | `cluster_tier` |

---

## Source Code Locations

All source files are located in:
`/Users/lucascruz/Documents/GitHub/vizu-mono/services/analytics_api/src/analytics_api/`

### Key Files

- **Schemas**: `schemas/metrics.py`, `schemas/views.py`
- **Endpoints**: `api/endpoints/*.py`
  - `dashboard.py` - Level 1 (Home)
  - `rankings.py` - Level 2 (Modules)
  - `deep_dive.py` - Level 3 (Details)
  - `indicators.py` - Indicators
  - `auth.py` - Authentication
  - `ingestion.py` - ETL triggers
- **Helpers**: `api/helpers.py`
- **Router**: `api/router.py`

---

## Notes

1. **Authentication**: All endpoints (except auth endpoints) require valid JWT token or client_id
2. **RLS (Row-Level Security)**: All gold table queries filter by `client_id` for data isolation
3. **Caching**: Indicators endpoint implements TTL-based caching
4. **Deprecated Endpoints**: `/api/dashboard/clientes/gold` should not be used; use `/api/clientes` instead
5. **URL Encoding**: Detail endpoint path parameters (e.g., `nome_cliente`) must be URL-encoded
6. **Pagination**: Not currently implemented; all endpoints return complete datasets with limits (e.g., top 10)
7. **Error Handling**: 404 for not found, 401 for unauthorized, 500 for server errors

---

**Document Version:** 1.0
**Last Updated:** 2026-01-15
**Generated by:** Claude Code Analysis
