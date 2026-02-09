# Frontend Data Interfaces - Vizu Dashboard

> Documentação completa de todas as interfaces TypeScript e funções de API disponíveis no frontend.  
> Atualizado em: 4 de fevereiro de 2026

---

## 📊 Interfaces de Dados

### 1. Pedidos

| Interface | Campos |
|-----------|--------|
| `Pedido` | `id`, `title`, `description`, `status`, `clientName`, `valorUnitario`, `enderecoEntrega`, `cnpjFaturamento`, `descricaoProdutos`, `valorTotal?`, `descricao?`, `frete?`, `quantidadeItens?` |
| `PedidoItem` | `order_id`, `data_transacao`, `id_cliente`, `ticket_pedido`, `qtd_produtos` |
| `PedidoItemDetalhe` | `raw_product_description`, `quantidade`, `valor_unitario`, `valor_total_emitter` |
| `PedidosOverviewResponse` | `scorecard_ticket_medio_por_pedido`, `scorecard_qtd_media_produtos_por_pedido`, `scorecard_taxa_recorrencia_clientes_perc`, `scorecard_recencia_media_entre_pedidos_dias`, `chart_pedidos_no_tempo[]`, `ranking_pedidos_por_regiao[]`, `ultimos_pedidos[]` |
| `PedidoDetailResponse` | `order_id`, `status_pedido`, `total_pedido`, `dados_cliente`, `itens_pedido[]` |

```typescript
interface Pedido {
  id: string;
  title: string;
  description: string;
  status: string;
  clientName: string;
  valorUnitario: string;
  enderecoEntrega: string;
  cnpjFaturamento: string;
  descricaoProdutos: string;
  valorTotal?: string;
  descricao?: string;
  frete?: string;
  quantidadeItens?: number;
}

interface PedidoItem {
  order_id: string;
  data_transacao: string;  // ISO date string
  id_cliente: string;
  ticket_pedido: number;
  qtd_produtos: number;
}

interface PedidoItemDetalhe {
  raw_product_description: string;
  quantidade: number;
  valor_unitario: number;
  valor_total_emitter: number;
}

interface PedidosOverviewResponse {
  scorecard_ticket_medio_por_pedido: number;
  scorecard_qtd_media_produtos_por_pedido: number;
  scorecard_taxa_recorrencia_clientes_perc: number;
  scorecard_recencia_media_entre_pedidos_dias: number;
  chart_pedidos_no_tempo: ChartDataPoint[];
  ranking_pedidos_por_regiao: ChartDataPoint[];
  ultimos_pedidos: PedidoItem[];
}

interface PedidoDetailResponse {
  order_id: string;
  status_pedido: string;
  total_pedido: number;
  dados_cliente: CadastralData;
  itens_pedido: PedidoItemDetalhe[];
}
```

---

### 2. Clientes

| Interface | Campos |
|-----------|--------|
| `RankingItem` | `nome`, `receita_total`, `quantidade_total`, `num_pedidos_unicos`, `primeira_venda`, `ultima_venda`, `ticket_medio`, `qtd_media_por_pedido`, `frequencia_pedidos_mes`, `recencia_dias`, `valor_unitario_medio`, `cluster_score`, `cluster_tier` |
| `ClientesOverviewResponse` | `scorecard_total_clientes`, `scorecard_ticket_medio_geral`, `scorecard_frequencia_media_geral`, `scorecard_crescimento_percentual?`, `chart_clientes_no_tempo[]`, `chart_receita_no_tempo[]`, `chart_ticketmedio_no_tempo[]`, `chart_quantidade_no_tempo[]`, `chart_clientes_por_regiao[]`, `chart_cohort_clientes[]`, `ranking_por_receita[]`, `ranking_por_ticket_medio[]`, `ranking_por_qtd_pedidos[]`, `ranking_por_cluster_vizu[]` |
| `ClienteDetailResponse` | `dados_cadastrais`, `scorecards`, `rankings_internos.mix_de_produtos_por_receita[]` |
| `CadastralData` | `emitter_nome?`, `emitter_cnpj?`, `emitter_telefone?`, `emitter_estado?`, `emitter_cidade?`, `receiver_nome?`, `receiver_cnpj?`, `receiver_telefone?`, `receiver_estado?`, `receiver_cidade?` |
| `CustomerMetricsResponse` | `total_active`, `new_customers`, `returning_customers`, `avg_lifetime_value`, `period`, `comparisons?` |

```typescript
interface RankingItem {
  nome: string;
  receita_total: number;
  quantidade_total: number;
  num_pedidos_unicos: number;
  primeira_venda: string;   // ISO date string
  ultima_venda: string;     // ISO date string
  ticket_medio: number;
  qtd_media_por_pedido: number;
  frequencia_pedidos_mes: number;
  recencia_dias: number;
  valor_unitario_medio: number;
  cluster_score: number;
  cluster_tier: string;
}

interface ClientesOverviewResponse {
  scorecard_total_clientes: number;
  scorecard_ticket_medio_geral: number;
  scorecard_frequencia_media_geral: number;
  scorecard_crescimento_percentual?: number | null;
  chart_clientes_no_tempo: ChartDataPoint[];
  chart_receita_no_tempo: ChartDataPoint[];
  chart_ticketmedio_no_tempo: ChartDataPoint[];
  chart_quantidade_no_tempo: ChartDataPoint[];
  chart_clientes_por_regiao: ChartDataPoint[];
  chart_cohort_clientes: ChartDataPoint[];
  ranking_por_receita: RankingItem[];
  ranking_por_ticket_medio: RankingItem[];
  ranking_por_qtd_pedidos: RankingItem[];
  ranking_por_cluster_vizu: RankingItem[];
}

interface ClienteDetailResponse {
  dados_cadastrais: CadastralData;
  scorecards: RankingItem | null;
  rankings_internos: {
    mix_de_produtos_por_receita: RankingItem[];
  };
}

interface CadastralData {
  emitter_nome?: string;
  emitter_cnpj?: string;
  emitter_telefone?: string;
  emitter_estado?: string;
  emitter_cidade?: string;
  receiver_nome?: string;
  receiver_cnpj?: string;
  receiver_telefone?: string;
  receiver_estado?: string;
  receiver_cidade?: string;
}

interface CustomerMetricsResponse {
  total_active: number;
  new_customers: number;
  returning_customers: number;
  avg_lifetime_value: number;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}
```

---

### 3. Fornecedores

| Interface | Campos |
|-----------|--------|
| `FornecedoresOverviewResponse` | `scorecard_total_fornecedores`, `scorecard_crescimento_percentual?`, `chart_fornecedores_no_tempo[]`, `chart_receita_no_tempo[]`, `chart_ticketmedio_no_tempo[]`, `chart_quantidade_no_tempo[]`, `chart_fornecedores_por_regiao[]`, `chart_cohort_fornecedores[]`, `ranking_por_receita[]`, `ranking_por_qtd_media[]`, `ranking_por_ticket_medio[]`, `ranking_por_frequencia[]`, `ranking_produtos_mais_vendidos[]` |
| `FornecedorDetailResponse` | `dados_cadastrais`, `rankings_internos.clientes_por_receita[]`, `rankings_internos.produtos_por_receita[]`, `rankings_internos.regioes_por_receita[]`, `charts.receita_no_tempo[]` |

```typescript
interface FornecedoresOverviewResponse {
  scorecard_total_fornecedores: number;
  scorecard_crescimento_percentual?: number | null;
  chart_fornecedores_no_tempo: ChartDataPoint[];
  chart_receita_no_tempo: ChartDataPoint[];
  chart_ticketmedio_no_tempo: ChartDataPoint[];
  chart_quantidade_no_tempo: ChartDataPoint[];
  chart_fornecedores_por_regiao: ChartDataPoint[];
  chart_cohort_fornecedores: ChartDataPoint[];
  ranking_por_receita: RankingItem[];
  ranking_por_qtd_media: RankingItem[];
  ranking_por_ticket_medio: RankingItem[];
  ranking_por_frequencia: RankingItem[];
  ranking_produtos_mais_vendidos: ProdutoRankingReceita[];
}

interface FornecedorDetailResponse {
  dados_cadastrais: CadastralData;
  rankings_internos: {
    clientes_por_receita: RankingItem[];
    produtos_por_receita: RankingItem[];
    regioes_por_receita: RankingItem[];
  };
  charts: {
    receita_no_tempo: ChartDataPoint[];
  };
}
```

---

### 4. Produtos

| Interface | Campos |
|-----------|--------|
| `ProdutoRankingReceita` | `nome`, `receita_total`, `valor_unitario_medio`, `quantidade_total`, `cluster_tier` |
| `ProdutoRankingVolume` | `nome`, `quantidade_total`, `valor_unitario_medio`, `receita_total`, `cluster_tier` |
| `ProdutoRankingTicket` | `nome`, `ticket_medio`, `valor_unitario_medio`, `quantidade_total`, `cluster_tier` |
| `ProdutosOverviewResponse` | `scorecard_total_itens_unicos`, `chart_produtos_no_tempo[]`, `chart_receita_no_tempo[]`, `chart_quantidade_no_tempo[]`, `ranking_por_receita[]`, `ranking_por_volume[]`, `ranking_por_ticket_medio[]` |
| `ProdutoDetailResponse` | `nome_produto`, `scorecards`, `charts.segmentos_de_clientes[]`, `rankings_internos.clientes_por_receita[]`, `rankings_internos.regioes_por_receita[]` |
| `ProductMetricsResponse` | `total_sold`, `unique_products`, `top_sellers[]`, `low_stock_alerts`, `avg_price`, `period`, `comparisons?` |

```typescript
interface ProdutoRankingReceita {
  nome: string;
  receita_total: number;
  valor_unitario_medio: number;
  quantidade_total: number;
  cluster_tier: string;
}

interface ProdutoRankingVolume {
  nome: string;
  quantidade_total: number;
  valor_unitario_medio: number;
  receita_total: number;
  cluster_tier: string;
}

interface ProdutoRankingTicket {
  nome: string;
  ticket_medio: number;
  valor_unitario_medio: number;
  quantidade_total: number;
  cluster_tier: string;
}

interface ProdutosOverviewResponse {
  scorecard_total_itens_unicos: number;
  chart_produtos_no_tempo: ChartDataPoint[];
  chart_receita_no_tempo: ChartDataPoint[];
  chart_quantidade_no_tempo: ChartDataPoint[];
  ranking_por_receita: ProdutoRankingReceita[];
  ranking_por_volume: ProdutoRankingVolume[];
  ranking_por_ticket_medio: ProdutoRankingTicket[];
}

interface ProdutoDetailResponse {
  nome_produto: string;
  scorecards: RankingItem | null;
  charts: {
    segmentos_de_clientes: ChartDataPoint[];
  };
  rankings_internos: {
    clientes_por_receita: RankingItem[];
    regioes_por_receita: RankingItem[];
  };
}

interface ProductMetricsResponse {
  total_sold: number;
  unique_products: number;
  top_sellers: any[];
  low_stock_alerts: number;
  avg_price: number;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}
```

---

### 5. Home/Dashboard

| Interface | Campos |
|-----------|--------|
| `HomeScorecards` | `receita_total`, `receita_mes_atual`, `total_fornecedores`, `total_produtos`, `total_regioes`, `total_clientes`, `total_pedidos`, `ticket_medio?`, `crescimento_receita?`, `frequencia_media_fornecedores?` |
| `HomeMetricsResponse` | `scorecards`, `charts[]` |
| `ChartDataPoint` | `name`, `[key: string]: any` (permite `total`, `percentual`, `contagem`, etc.) |
| `ChartData` | `id`, `title`, `data[]` |
| `OrderMetricsResponse` | `total`, `revenue`, `avg_order_value`, `growth_rate?`, `by_status`, `period`, `comparisons?` |

```typescript
interface HomeScorecards {
  receita_total: number;
  receita_mes_atual: number;  // Receita apenas do mês corrente
  total_fornecedores: number;
  total_produtos: number;
  total_regioes: number;
  total_clientes: number;
  total_pedidos: number;
  ticket_medio?: number;
  crescimento_receita?: number;
  frequencia_media_fornecedores?: number;  // Média de pedidos por fornecedor por mês
}

interface HomeMetricsResponse {
  scorecards: HomeScorecards;
  charts: ChartData[];
}

interface ChartDataPoint {
  name: string;
  [key: string]: any;  // Allows for 'total', 'percentual', 'contagem', etc.
}

interface ChartData {
  id: string;
  title: string;
  data: ChartDataPoint[];
}

interface OrderMetricsResponse {
  total: number;
  revenue: number;
  avg_order_value: number;
  growth_rate: number | null;
  by_status: Record<string, any>;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}
```

---

### 6. Geo/Mapas

| Interface | Campos |
|-----------|--------|
| `GeoCluster` | `location`, `count`, `total_revenue`, `coordinates[lat, lng]` |
| `GeoClustersResponse` | `clusters[]`, `center[lat, lng]`, `max_count`, `total_clusters` |

```typescript
interface GeoCluster {
  location: string;
  count: number;
  total_revenue: number;
  coordinates: [number, number];  // [lat, lng]
}

interface GeoClustersResponse {
  clusters: GeoCluster[];
  center: [number, number];
  max_count: number;
  total_clusters: number;
}
```

---

### 7. Filtros/Análise Cruzada

| Interface | Campos |
|-----------|--------|
| `ProductFilterItem` | `nome`, `receita_total`, `total_clientes` |
| `CustomerFilterItem` | `customer_cpf_cnpj`, `nome`, `receita_total`, `total_produtos` |
| `CustomerByProduct` | `customer_cpf_cnpj`, `nome`, `produto_receita`, `produto_quantidade`, `produto_pedidos`, `cliente_receita_total`, `percentual_do_total` |
| `ProductByCustomer` | `nome`, `receita_total`, `quantidade_total`, `num_pedidos`, `valor_unitario_medio` |
| `CustomerBySupplier` | `nome`, `customer_cpf_cnpj`, `receita_total`, `quantidade_total`, `num_pedidos`, `ticket_medio` |
| `SupplierByProduct` | `supplier_id`, `supplier_name`, `supplier_cnpj`, `endereco_cidade?`, `endereco_uf?`, `quantity_sold`, `total_revenue`, `order_count`, `avg_unit_price`, `last_sale?` |
| `MonthlyOrderData` | `month`, `num_pedidos` |

```typescript
interface ProductFilterItem {
  nome: string;
  receita_total: number;
  total_clientes: number;
}

interface CustomerFilterItem {
  customer_cpf_cnpj: string;
  nome: string;
  receita_total: number;
  total_produtos: number;
}

interface CustomerByProduct {
  customer_cpf_cnpj: string;
  nome: string;
  produto_receita: number;
  produto_quantidade: number;
  produto_pedidos: number;
  cliente_receita_total: number;
  percentual_do_total: number;
}

interface ProductByCustomer {
  nome: string;
  receita_total: number;
  quantidade_total: number;
  num_pedidos: number;
  valor_unitario_medio: number;
}

interface CustomerBySupplier {
  nome: string;
  customer_cpf_cnpj: string;
  receita_total: number;
  quantidade_total: number;
  num_pedidos: number;
  ticket_medio: number;
}

interface SupplierByProduct {
  supplier_id: string;
  supplier_name: string;
  supplier_cnpj: string;
  endereco_cidade: string | null;
  endereco_uf: string | null;
  quantity_sold: number;
  total_revenue: number;
  order_count: number;
  avg_unit_price: number;
  last_sale: string | null;
}

interface MonthlyOrderData {
  month: string;    // YYYY-MM format
  num_pedidos: number;
}
```

---

### 8. Materialized Views (Fast Data)

| Interface | Campos |
|-----------|--------|
| `MVCustomerSummary` | `customer_id`, `name`, `cpf_cnpj`, `estado?`, `total_orders`, `lifetime_value`, `avg_order_value`, `total_quantity`, `last_order_date?`, `first_order_date?`, `days_since_last_order` |
| `MVCustomersResponse` | `customers[]`, `total` |
| `MVProductSummary` | `product_id`, `product_name`, `times_sold`, `total_quantity_sold`, `total_revenue`, `avg_order_value`, `avg_price`, `min_price`, `max_price`, `last_sold_date?`, `unique_customers` |
| `MVProductsResponse` | `products[]`, `total` |
| `MVMonthlySales` | `month`, `name`, `orders`, `unique_customers`, `revenue`, `total`, `avg_order_value` |
| `MVMonthlySalesResponse` | `monthly_sales[]`, `total_months` |
| `MVDashboardSummary` | `total_customers`, `total_products`, `total_orders`, `total_revenue`, `avg_order_value`, `monthly_trend[]`, `top_customers[]`, `top_products[]` |

```typescript
interface MVCustomerSummary {
  customer_id: string;
  name: string;
  cpf_cnpj: string;
  estado: string | null;
  total_orders: number;
  lifetime_value: number;
  avg_order_value: number;
  total_quantity: number;
  last_order_date: string | null;
  first_order_date: string | null;
  days_since_last_order: number;
}

interface MVCustomersResponse {
  customers: MVCustomerSummary[];
  total: number;
}

interface MVProductSummary {
  product_id: string;
  product_name: string;
  times_sold: number;
  total_quantity_sold: number;
  total_revenue: number;
  avg_order_value: number;
  avg_price: number;
  min_price: number;
  max_price: number;
  last_sold_date: string | null;
  unique_customers: number;
}

interface MVProductsResponse {
  products: MVProductSummary[];
  total: number;
}

interface MVMonthlySales {
  month: string;          // YYYY-MM format
  name: string;           // Same as month, for chart compatibility
  orders: number;
  unique_customers: number;
  revenue: number;
  total: number;          // Same as revenue, for chart compatibility
  avg_order_value: number;
}

interface MVMonthlySalesResponse {
  monthly_sales: MVMonthlySales[];
  total_months: number;
}

interface MVDashboardSummary {
  total_customers: number;
  total_products: number;
  total_orders: number;
  total_revenue: number;
  avg_order_value: number;
  monthly_trend: MVMonthlySales[];
  top_customers: MVCustomerSummary[];
  top_products: MVProductSummary[];
}
```

---

### 9. Auth

| Interface | Campos |
|-----------|--------|
| `MeResponse` | `client_id` |

```typescript
interface MeResponse {
  client_id: string;
}
```

---

## 📌 Funções de API Disponíveis

### Pedidos
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getPedidosOverview()` | `GET /pedidos` | `PedidosOverviewResponse` |
| `getPedidoDetails(order_id)` | `GET /pedido/{order_id}` | `PedidoDetailResponse` |

### Fornecedores
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getFornecedores(period)` | `GET /fornecedores` | `FornecedoresOverviewResponse` |
| `getFornecedor(nome)` | `GET /fornecedor/{nome}/gold` | `FornecedorDetailResponse` |

### Clientes
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getClientes(period)` | `GET /clientes` | `ClientesOverviewResponse` |
| `getCliente(nome)` | `GET /cliente/{nome}/gold` | `ClienteDetailResponse` |

### Produtos
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getProdutosOverview(period)` | `GET /produtos` | `ProdutosOverviewResponse` |
| `getProdutoDetails(nome)` | `GET /produto/{nome}/gold` | `ProdutoDetailResponse` |

### Dashboard/Home
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getHomeMetrics()` | `GET /dashboard/home_gold` | `HomeMetricsResponse` |

### Indicators
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getCustomerIndicators(period, includeComparisons)` | `GET /indicators/customers` | `CustomerMetricsResponse` |
| `getProductIndicators(period, includeComparisons)` | `GET /indicators/products` | `ProductMetricsResponse` |
| `getOrderIndicators(period, includeComparisons)` | `GET /indicators/orders` | `OrderMetricsResponse` |

### Geo
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getGeoClusters(groupBy)` | `GET /dashboard/clientes/geo-clusters` | `GeoClustersResponse` |

### Filtros/Análise Cruzada
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getProductsForFilter()` | `GET /filters/products` | `ProductFilterItem[]` |
| `getCustomersForFilter()` | `GET /filters/customers` | `CustomerFilterItem[]` |
| `getCustomersByProduct(productName, limit)` | `GET /customers-by-product/{name}` | `CustomerByProduct[]` |
| `getProductsByCustomer(customerCpfCnpj, limit)` | `GET /products-by-customer/{cpf}` | `ProductByCustomer[]` |
| `getCustomerMonthlyOrders(customerCpfCnpj)` | `GET /customer-monthly-orders/{cpf}` | `MonthlyOrderData[]` |
| `getCustomersBySupplier(supplierCnpj, limit)` | `GET /customers-by-supplier/{cnpj}` | `CustomerBySupplier[]` |
| `getProductsBySupplier(supplierCnpj, limit)` | `GET /products-by-supplier/{cnpj}` | `ProductByCustomer[]` |
| `getSuppliersByProduct(productName, limit)` | `GET /suppliers-by-product/{name}` | `SupplierByProduct[]` |

### Auth
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getMe(token)` | `GET /dashboard/me` | `MeResponse` |

### Materialized Views
| Função | Endpoint | Retorno |
|--------|----------|---------|
| `getMVCustomers()` | `GET /dashboard/mv/customers` | `MVCustomersResponse` |
| `getMVProducts()` | `GET /dashboard/mv/products` | `MVProductsResponse` |
| `getMVMonthlySales()` | `GET /dashboard/mv/monthly-sales` | `MVMonthlySalesResponse` |
| `getMVDashboardSummary()` | `GET /dashboard/mv/summary` | `MVDashboardSummary` |

---

## 📁 Localização do Arquivo

Todas as interfaces e funções estão definidas em:

```
apps/vizu_dashboard/src/services/analyticsService.ts
```

---

## 🔗 Relacionamentos Entre Interfaces

```
HomeMetricsResponse
├── HomeScorecards
└── ChartData[]
    └── ChartDataPoint[]

FornecedoresOverviewResponse
├── ChartDataPoint[] (múltiplos charts)
├── RankingItem[] (rankings de fornecedores)
└── ProdutoRankingReceita[] (ranking produtos)

FornecedorDetailResponse
├── CadastralData
├── RankingItem[] (clientes, produtos, regiões)
└── ChartDataPoint[] (receita no tempo)

ClientesOverviewResponse
├── ChartDataPoint[] (múltiplos charts)
└── RankingItem[] (múltiplos rankings)

ClienteDetailResponse
├── CadastralData
├── RankingItem (scorecards)
└── RankingItem[] (mix de produtos)

ProdutosOverviewResponse
├── ChartDataPoint[] (charts de produtos)
├── ProdutoRankingReceita[]
├── ProdutoRankingVolume[]
└── ProdutoRankingTicket[]

ProdutoDetailResponse
├── RankingItem (scorecards)
├── ChartDataPoint[] (segmentos)
└── RankingItem[] (clientes, regiões)

MVDashboardSummary
├── MVMonthlySales[]
├── MVCustomerSummary[]
└── MVProductSummary[]
```
