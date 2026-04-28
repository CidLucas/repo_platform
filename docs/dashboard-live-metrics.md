# Dashboard — Live Metrics Map

This document catalogs every **UI element on the user-facing dashboard** (`/dashboard/**`) whose value is pulled from the database, along with the exact query behind it.

All queries run against the `analytics_v2` schema over PostgREST (`supabase.schema('analytics_v2').from(...)`) and are constrained by RLS (`client_id = public.get_my_client_id()`). The schema was slimmed and refactored in the Apr 2026 cleanup — see [`memories/repo/analytics-v2-cleanup-apr2026.md`](../memories/repo/analytics-v2-cleanup-apr2026.md).

Code citations point at files under [`apps/blu_dashboard/src`](../apps/blu_dashboard/src).

---

## 1. Home — `/dashboard` → [`HomePage.tsx`](../apps/blu_dashboard/src/pages/HomePage.tsx)

Hook: `useHomeMetrics()` → calls [`getHomeMetrics()`](../apps/blu_dashboard/src/services/analyticsService.ts#L919) in `analyticsService.ts`.

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

| Card         | Big number field     | Sublabel / sublabel field                |
| ------------ | -------------------- | ---------------------------------------- |
| Clientes     | `total_clientes`     | `clientes_ativos` → "ativos"             |
| Fornecedores | `total_fornecedores` | `frequencia_media_fornecedores`          |
| Produtos     | `total_produtos`     | `quantidade_total_vendida`               |
| Pedidos      | `total_pedidos`      | `ticket_medio` (shown as "Ticket Médio") |

### 1.3 KPI — Ticket Médio

Field: `ticket_medio` from same `v_resumo_dashboard` row.

### 1.4 Domain Expansion Modal (click on a Domain card)

Opened by `DomainExpansionModal` → [`getDomainAnalytics(domain)`](../apps/blu_dashboard/src/services/analyticsService.ts#L1468).

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

| domain    | KPIs                                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| orders    | `total_pedidos`, `ticket_medio`, `crescimento_receita`                                   |
| customers | `clientes_ativos`, `total_clientes`, `ticket_medio` (as avg_ltv), `crescimento_clientes` |
| suppliers | `total_fornecedores`, `receita_total`                                                    |
| products  | `total_produtos`, `quantidade_total_vendida`, `receita_total`                            |

---

## 2. Pedidos — `/dashboard/pedidos` → [`PedidosPage.tsx`](../apps/blu_dashboard/src/pages/PedidosPage.tsx)

Two parallel calls on mount / period change:

- [`getPedidosOverview()`](../apps/blu_dashboard/src/services/analyticsService.ts#L362)
- [`getOrderIndicators(period)`](../apps/blu_dashboard/src/services/analyticsService.ts#L973)

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

Triggered by click on a ListCard item → [`getPedidoDetails(order_id)`](../apps/blu_dashboard/src/services/analyticsService.ts#L436):

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

## 3. Dimension Pages (Deprecated)

The legacy pages `/dashboard/clientes`, `/dashboard/fornecedores`, `/dashboard/produtos` and their `/lista` variants were removed during the dashboard migration.

Current behavior:

- All these legacy paths now redirect to `/dashboard`.
- The primary analytical interaction is now the expandable domain card flow in [`HomePage.tsx`](../apps/blu_dashboard/src/pages/HomePage.tsx) via [`DomainExpansionModal.tsx`](../apps/blu_dashboard/src/components/DomainExpansionModal.tsx).

The underlying analytics sources remain in `analyticsService.ts` and `analytics_v2`, but they are no longer surfaced through dedicated per-dimension pages.

---

## 4. Geo Cluster Source (Still Active)

Geo clustering remains active for map visualizations and is sourced from:

```sql
SELECT endereco_uf, endereco_cidade, receita_total
FROM analytics_v2.dim_clientes;
```

Implementation reference:

- [`getGeoClusters(groupBy)`](../apps/blu_dashboard/src/services/analyticsService.ts#L1561)

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

| View consumed by UI       | Underlying MV              |
| ------------------------- | -------------------------- |
| `v_resumo_dashboard`      | `mv_resumo_dashboard`      |
| `v_series_temporal`       | `mv_series_temporal`       |
| `v_distribuicao_regional` | `mv_distribuicao_regional` |
| `v_ultimos_pedidos`       | `mv_ultimos_pedidos`       |

MVs are refreshed by `analytics_v2.atualizar_agregados(client_id text)` at the end of each ingestion run.
