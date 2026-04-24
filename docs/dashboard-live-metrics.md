# Dashboard — Live Metrics Map

This document catalogs every **UI element on the user-facing dashboard** (`/dashboard/**`) whose value is pulled from the database, along with the exact query behind it.

All queries run against the `analytics_v2` schema over PostgREST (`supabase.schema('analytics_v2').from(...)`) and are constrained by RLS (`client_id = public.get_my_client_id()`). The schema was slimmed and refactored in the Apr 2026 cleanup — see [`memories/repo/analytics-v2-cleanup-apr2026.md`](../memories/repo/analytics-v2-cleanup-apr2026.md).

Code citations point at files under [`apps/vizu_dashboard/src`](../apps/vizu_dashboard/src).

---

## 1. Home — `/dashboard` → [`HomePage.tsx`](../apps/vizu_dashboard/src/pages/HomePage.tsx)

Hook: `useHomeMetrics()` → calls [`getHomeMetrics()`](../apps/vizu_dashboard/src/services/analyticsService.ts#L919) in `analyticsService.ts`.

### 1.1 Revenue header ("Revenue" big number + month number)

**UI fields:** `Revenue` big number, `Revenue this month` sub-figure, growth arrow.

**Query** (`analyticsService.ts` ~ L919):
```sql
SELECT * FROM analytics_v2.v_resumo_dashboard LIMIT 1;
```
Fields consumed from the single row:
- `receita_total` → Revenue big number
- `receita_mes_atual` → "Revenue this month"
- `crescimento_receita` → growth % arrow

### 1.2 Domain cards (Clientes / Fornecedores / Produtos / Pedidos)

**Same query as 1.1** (`SELECT * FROM v_resumo_dashboard LIMIT 1`).

| Card | Big number field | Sublabel / sublabel field |
|---|---|---|
| Clientes | `total_clientes` | `clientes_ativos` → "ativos" |
| Fornecedores | `total_fornecedores` | `frequencia_media_fornecedores` |
| Produtos | `total_produtos` | `quantidade_total_vendida` |
| Pedidos | `total_pedidos` | `ticket_medio` (shown as "Ticket Médio") |

### 1.3 KPI — Ticket Médio

Field: `ticket_medio` from same `v_resumo_dashboard` row.

### 1.4 Domain Expansion Modal (click on a Domain card)

Opened by `DomainExpansionModal` → [`getDomainAnalytics(domain)`](../apps/vizu_dashboard/src/services/analyticsService.ts#L1468).

Two queries per click:

```sql
-- (a) Scorecards
SELECT * FROM analytics_v2.v_resumo_dashboard LIMIT 1;

-- (b) Monthly trend chart (tipo_grafico varies by domain)
SELECT *
FROM analytics_v2.v_series_temporal
WHERE tipo_grafico = $1      -- 'receita' | 'clientes' | 'fornecedores' | 'produtos'
ORDER BY data_periodo ASC;
```

KPI mapping per domain (all fields come from `v_resumo_dashboard`):

| domain | KPIs |
|---|---|
| orders | `total_pedidos`, `ticket_medio`, `crescimento_receita` |
| customers | `clientes_ativos`, `total_clientes`, `ticket_medio` (as avg_ltv), `crescimento_clientes` |
| suppliers | `total_fornecedores`, `receita_total` |
| products | `total_produtos`, `quantidade_total_vendida`, `receita_total` |

---

## 2. Pedidos — `/dashboard/pedidos` → [`PedidosPage.tsx`](../apps/vizu_dashboard/src/pages/PedidosPage.tsx)

Two parallel calls on mount / period change:
- [`getPedidosOverview()`](../apps/vizu_dashboard/src/services/analyticsService.ts#L362)
- [`getOrderIndicators(period)`](../apps/vizu_dashboard/src/services/analyticsService.ts#L973)

### 2.1 Header scorecards — "Total de Pedidos" / "Concluídos" / "Pendentes"

Source: `getOrderIndicators()` (L973). Query:

```sql
SELECT * FROM analytics_v2.v_resumo_dashboard LIMIT 1;
```

Mapping:
- `total` → `total_pedidos`
- `revenue` → `receita_total`
- `avg_order_value` → `ticket_medio`
- `growth_rate` → `crescimento_receita`
- `by_status.completed` → `total_pedidos` (single-bucket; see placeholders doc for the pending-status limitation)

### 2.2 Card "Métricas de Pedidos"

Scorecard value, bar chart and KPI items are all computed client-side from the object returned in 2.1 (`total`, `revenue`, `avg_order_value`, `growth_rate`).

### 2.3 Card "Volume de Pedidos"

Series from `getPedidosOverview()`:

```sql
SELECT *
FROM analytics_v2.v_series_temporal
WHERE tipo_grafico = 'pedidos'
  AND dimensao    = 'total'
ORDER BY data_periodo ASC;
```

Chart plots `total_cumulativo` per period (field present in `v_series_temporal`).

### 2.4 Card "Últimos Pedidos" (ListCard)

```sql
SELECT *
FROM analytics_v2.v_ultimos_pedidos
ORDER BY ordem ASC
LIMIT 50;
```
Each item renders `pedido_id`, `cliente_cpf_cnpj`, `valor_pedido`, `qtd_produtos`.

### 2.5 Pedido Details Modal

Triggered by click on a ListCard item → [`getPedidoDetails(order_id)`](../apps/vizu_dashboard/src/services/analyticsService.ts#L436):

```sql
SELECT
  documento, valor, quantidade, valor_unitario,
  dim_clientes (nome, cpf_cnpj, telefone, endereco_uf, endereco_cidade),
  dim_inventory!inventory_id (nome),
  dim_datas!data_competencia_id (data)
FROM analytics_v2.fato_transacoes
WHERE documento = $1;   -- order_id
```

---

## 3. Clientes / Fornecedores / Produtos — Overview pages

All three pages are rendered by a single generic component [`GenericOverviewPage.tsx`](../apps/vizu_dashboard/src/pages/GenericOverviewPage.tsx), driven by a dimension config (`clientesConfig.tsx`, `fornecedoresConfig.tsx`, `produtosConfig.tsx`). Every card below gets its data from **one underlying fetch per page**, plus a shared geo-cluster fetch for the map.

Main fetch functions:
- Clientes → [`getClientesOverview()`](../apps/vizu_dashboard/src/services/analyticsService.ts#L613)
- Fornecedores → [`getFornecedoresOverview()`](../apps/vizu_dashboard/src/services/analyticsService.ts#L480)
- Produtos → [`getProdutosOverview()`](../apps/vizu_dashboard/src/services/analyticsService.ts#L757)

### 3.1 Overview payload — shared shape

Each `get*Overview()` issues 3 parallel queries, for example Clientes:

```sql
-- (a) Dim rows (used for rankings + ticker aggregations)
SELECT * FROM analytics_v2.dim_clientes
ORDER BY receita_total DESC;

-- (b) Time series (drives performance-card charts)
SELECT *
FROM analytics_v2.v_series_temporal
WHERE tipo_grafico = 'clientes'      -- or 'fornecedores' / 'produtos'
ORDER BY data_periodo ASC;

-- (c) Regional distribution (feeds map fallback)
SELECT *
FROM analytics_v2.v_distribuicao_regional
WHERE tipo_grafico = 'pedidos_por_regiao'
ORDER BY total DESC;
```

Fornecedores uses `dim_fornecedores`, Produtos uses `dim_inventory` — everything else is identical.

### 3.2 Stat block "TOTAL DE …"

Source: the dimension count derived from the overview response.

| Page | Field (from overview response) | Origin |
|---|---|---|
| Clientes | `scorecard_total_clientes` | row count of `dim_clientes` |
| Fornecedores | `scorecard_total_fornecedores` | row count of `dim_fornecedores` |
| Produtos | `scorecard_total_produtos` | row count of `dim_inventory` |

### 3.3 Growth message in header

Field: `scorecard_crescimento_percentual` — computed client-side from `v_series_temporal` period-over-period.

### 3.4 Performance Card — 4 slides (Receita / Ticket Médio / Pedidos / Volume)

Each slide combines a chart and a rank.

| Slide | Chart field (from time series) | Ranking source |
|---|---|---|
| Receita | `chart_receita_no_tempo` | `ranking_por_receita` (sorted by `receita_total`) |
| Ticket Médio | `chart_ticketmedio_no_tempo` | `ranking_por_ticket_medio` |
| Pedidos | `chart_clientes_no_tempo` / `chart_produtos_no_tempo` | `ranking_por_qtd_pedidos` |
| Volume | `chart_clientes_no_tempo` / `chart_produtos_no_tempo` | `ranking_por_volume` |

All come from the single `v_series_temporal` query in 3.1 (b), bucketed by `dimensao` (`receita`, `ticket_medio`, `contagem`, `quantidade`).

### 3.5 Insights Card — scorecard + bullets

- Scorecard `Novos Cadastros` (Clientes): number of ranking entries where `primeira_venda ≥ now() - 30d`.
- Bullets: tier distribution (`cluster_tier` on each ranking row), growth, top entity, ticket médio — all derived from the dim rows returned in 3.1 (a).
- Optional carousel: tier count / tier avg-ticket / tier revenue from `scorecard_tier_{a|b|c|d}_{count|ticket_medio|receita}` columns on the dim table.

### 3.6 List Card — "Top X by selected metric"

Same ranking arrays as the performance slides, re-mapped by `listCard.rankingKeyMap[selectedMetric]`.

### 3.7 Map Card — "Distribuição Geográfica"

Hook: [`useGeoClusters('state')`](../apps/vizu_dashboard/src/hooks/useGeoClusters.ts) → [`getGeoClusters(groupBy)`](../apps/vizu_dashboard/src/services/analyticsService.ts#L1022).

```sql
SELECT endereco_uf, endereco_cidade, total_pedidos, receita_total
FROM analytics_v2.dim_clientes;
```

Clients are bucketed by UF in JS; each cluster is plotted using a static Brazilian state-capital lookup (`STATE_COORDINATES`) inside `analyticsService.ts`.

### 3.8 Detail Modal (click on a ranking item)

Opens `GenericDetailsModal` → calls `services.getDetail(item.id)`:

```sql
-- Clientes (getCliente, ~L713)
SELECT * FROM analytics_v2.dim_clientes WHERE nome = $1 LIMIT 1;
SELECT * FROM analytics_v2.get_client_top_products($1);           -- RPC
SELECT * FROM analytics_v2.get_client_monthly_orders($1);         -- RPC via getCustomerMonthlyOrders
SELECT * FROM analytics_v2.get_client_top_regions($1);            -- RPC

-- Fornecedores (getFornecedor, ~L574)
SELECT * FROM analytics_v2.dim_fornecedores WHERE nome = $1 LIMIT 1;
SELECT * FROM analytics_v2.get_supplier_top_clients($1);          -- RPC
SELECT * FROM analytics_v2.get_supplier_top_products($1);         -- RPC
SELECT * FROM analytics_v2.get_supplier_top_regions($1);          -- RPC
SELECT * FROM analytics_v2.get_supplier_revenue_series($1);       -- RPC

-- Produtos (getProduto, ~L871)
SELECT * FROM analytics_v2.dim_inventory WHERE nome = $1 LIMIT 1;
SELECT * FROM analytics_v2.get_product_top_clients($1);           -- RPC
SELECT * FROM analytics_v2.get_product_top_regions($1);           -- RPC
SELECT * FROM analytics_v2.get_product_revenue_series($1);        -- RPC
```

### 3.9 Expandable Scorecard (Clientes modal — "Frequência de Compra")

```sql
SELECT * FROM analytics_v2.get_client_monthly_orders($cnpj);
```
Returns `{ month, num_pedidos }[]` — plotted as a line chart inside the modal.

---

## 4. List pages — `/dashboard/{clientes|fornecedores|produtos}/lista`

Rendered by [`GenericListPage.tsx`](../apps/vizu_dashboard/src/pages/GenericListPage.tsx). Data is loaded by `config.hooks.useListData()`, which wraps the same overview fetch as 3.1 and optionally one of the cross-entity RPCs for the active "view mode":

| View mode | Query |
|---|---|
| `all` | Returns `ranking_por_receita` from overview response. |
| `by-product` | `SELECT * FROM analytics_v2.get_product_top_clients($1)` (Clientes) / `get_product_top_suppliers` (Fornecedores) |
| `by-customer` | `SELECT * FROM analytics_v2.get_client_top_products($1)` |
| `by-supplier` | `SELECT * FROM analytics_v2.get_supplier_top_clients($1)` |

Each mode has its own `tableColumns` definition in the dimension config — every cell value is pulled directly from the returned row fields (e.g. `receita_total`, `ticket_medio`, `num_pedidos`, `cluster_tier`).

### Pedidos list — `/dashboard/pedidos/lista`

Reuses the same `v_ultimos_pedidos` query (2.4) without the `LIMIT 50` clamp.

---

## 5. Reference — Full `v_resumo_dashboard` column list

As of the Apr 2026 cleanup, `v_resumo_dashboard` exposes exactly these columns (all consumed by the UI):

```
client_id, total_clientes, total_fornecedores, total_produtos, total_pedidos,
receita_total, ticket_medio, quantidade_total_vendida,
receita_mes_atual, quantidade_mes_atual, clientes_mes_atual,
produtos_mes_atual, fornecedores_mes_atual,
crescimento_receita, crescimento_clientes, crescimento_produtos, crescimento_quantidade,
frequencia_media_fornecedores, total_regioes, ultimo_mes,
clientes_ativos, clientes_novos, gerado_em
```

## 6. Reference — Materialized views powering the views

| View consumed by UI | Underlying MV |
|---|---|
| `v_resumo_dashboard` | `mv_resumo_dashboard` |
| `v_series_temporal` | `mv_series_temporal` |
| `v_distribuicao_regional` | `mv_distribuicao_regional` |
| `v_ultimos_pedidos` | `mv_ultimos_pedidos` |

MVs are refreshed by `analytics_v2.atualizar_agregados(client_id text)` at the end of each ingestion run.
