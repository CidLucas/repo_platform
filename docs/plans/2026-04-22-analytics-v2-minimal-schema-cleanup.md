# Analytics V2 — Minimal Schema Cleanup

> **For Claude Opus Work Session**
> **Project:** Releases de produto
> **Repository:** vizu-mono
> **Target schema:** `analytics_v2`

---

## Executive Summary

**Goal:** Shrink `analytics_v2` down to the _minimum_ set of tables and columns required by the new Onboarding + Dashboard frontends, removing ~3 years of accumulated ingestion experiments.

**Approach:** Freeze the current UI as the **source of truth** for required metrics. Map every metric back to a single canonical column. Drop everything that is not referenced. Then rewrite the ingestion pipeline and dashboard views to speak the minimal schema.

**Estimated Complexity:** Medium (schema is polluted, but UI surface is small).

**Key Dependencies (existing libs to reuse):**

- `supabase/migrations/` — DDL workflow
- `libs/vizu_data_connectors/` — FDW → staging transforms
- `libs/vizu_supabase_client/` — RLS-aware client
- Existing views pattern (`v_resumo_dashboard`, `v_series_temporal`, `v_distribuicao_regional`, `v_ultimos_pedidos`, `v_produtos_por_cliente`)
- Existing RPCs: `get_*_top_clients`, `get_*_top_products`, `get_*_top_regions`, `get_*_revenue_series`

---

## Phase 0 — Discovery Summary

### Frontend surface analysed

| App / Page                                                                     | File                                                                                                                                                                                     | Role                                                                  |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Onboarding (Auth → BusinessDNA → DataFork → Agents → CommandRules → LaunchPad) | [apps/landing/src/onboarding/steps/](apps/landing/src/onboarding/steps/)                                                                                                                 | Collects tenant metadata + agent config. **No analytics reads.**      |
| Home dashboard                                                                 | [apps/vizu_dashboard/src/pages/HomePage.tsx](apps/vizu_dashboard/src/pages/HomePage.tsx)                                                                                                 | KPI tiles + domain cards (Pedidos, Clientes, Fornecedores, Produtos). |
| Pedidos                                                                        | [apps/vizu_dashboard/src/pages/PedidosPage.tsx](apps/vizu_dashboard/src/pages/PedidosPage.tsx)                                                                                           | Totals, volume over time, últimos pedidos, detail modal.              |
| Clientes / Fornecedores / Produtos                                             | [apps/vizu_dashboard/src/pages/GenericOverviewPage.tsx](apps/vizu_dashboard/src/pages/GenericOverviewPage.tsx), [GenericListPage.tsx](apps/vizu_dashboard/src/pages/GenericListPage.tsx) | Overviews, rankings, cluster tiers A–D, cross-entity drill-ins.       |
| All analytics reads                                                            | [apps/vizu_dashboard/src/services/analyticsService.ts](apps/vizu_dashboard/src/services/analyticsService.ts)                                                                             | Single choke-point — every field below originates here.               |

### Existing schema (current, polluted)

`analytics_v2` currently contains (non-exhaustive):

- **Dimension duplicates from historical renames:** `dim_customer`, `clientes`, `dim_clientes`; `dim_supplier`, `fornecedores`, `dim_fornecedores`; `dim_product`, `produtos`, `dim_inventory`; `dim_date`, `datas`, `dim_datas`.
- **Fact duplicates:** `fact_sales` → renamed `vendas`; `fato_transacoes` (current target); `compras`; `fact_customer_product`; `fact_reservations`; `fact_availability`.
- **Out-of-scope tables:** `dim_resources`, `fact_reservations`, `fact_availability`, `dim_categoria`, `erp_purchase_orders`, `erp_purchase_order_items`, `compras`.
- **`fato_transacoes` wide columns** (from [20260422190000_multi_table_invoice_etl.sql](supabase/migrations/20260422190000_multi_table_invoice_etl.sql#L387)): 40+ columns including `nf_numero`, `danfe`, `is_blocked`, `volume`, `volume_validado`, `valor_validado`, `id_credito`, `data_credito`, `status_produto`, `data_criacao_produto`, `was_purchased`, `was_compensation`, `compensations_ids`, `purchase_order_ids`, `purchase_order_codes`, `in_offer`, `has_credit`, `product_invalidations`, `cpl_adicional`, `fisco_adicional`, `danfe_materials`, `filial_id`, `filial_cnpj` — **none are read by the UI**.

---

## Phase 1 — Required Metrics Inventory (UI → Column)

This is the **authoritative** list. Anything not in this table should be dropped.

### 1.1 HomePage ([HomePage.tsx](apps/vizu_dashboard/src/pages/HomePage.tsx))

| UI element                                                     | Metric                                                                     | Source               |
| -------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------- |
| "Revenue this month" big number                                | `receita_mes_atual` (fallback `receita_total`)                             | `v_resumo_dashboard` |
| Revenue growth %                                               | `crescimento_receita`                                                      | `v_resumo_dashboard` |
| Active tasks / Pedidos tile                                    | `total_pedidos`                                                            | `v_resumo_dashboard` |
| Ticket médio (KPI)                                             | `ticket_medio`                                                             | `v_resumo_dashboard` |
| Domain cards (4): Pedidos / Clientes / Fornecedores / Produtos | `total_pedidos`, `clientes_ativos`, `total_fornecedores`, `total_produtos` | `v_resumo_dashboard` |

### 1.2 PedidosPage ([PedidosPage.tsx](apps/vizu_dashboard/src/pages/PedidosPage.tsx))

| UI element                               | Metric                                                                                                            | Source                                               |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Total / concluídos / pendentes           | `total_pedidos`, `by_status`                                                                                      | aggregate of `fato_transacoes`                       |
| Receita do período, ticket médio, growth | `revenue`, `avg_order_value`, `growth_rate`                                                                       | `v_resumo_dashboard`                                 |
| Volume pedidos no tempo                  | cumulative count by month                                                                                         | `v_series_temporal` (tipo=`pedidos`, dim=`total`)    |
| Últimos pedidos                          | `pedido_id`, `data_transacao`, `cliente_cpf_cnpj`, `valor_pedido`, `qtd_produtos`                                 | `v_ultimos_pedidos`                                  |
| Regional distribution                    | `estado`/`regiao`, `total`                                                                                        | `v_distribuicao_regional`                            |
| Detail modal                             | `documento`, `valor`, `quantidade`, `valor_unitario`, cliente (nome/cnpj/telefone/uf/cidade), item (nome produto) | `fato_transacoes` + `dim_clientes` + `dim_inventory` |

### 1.3 Clientes ([analyticsService.ts#getClientes](apps/vizu_dashboard/src/services/analyticsService.ts))

| UI element                                                | Metric                                                                                                                                                                                         | Source                               |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| Scorecards                                                | `count(*)`, `avg(ticket_medio)`, `avg(frequencia_mensal)`, growth                                                                                                                              | `dim_clientes` + `v_series_temporal` |
| Tier breakdown (A/B/C/D) × count / receita / ticket_medio | `nivel_cluster`, `receita_total`, `ticket_medio`                                                                                                                                               | `dim_clientes`                       |
| Series (count / receita / quantidade)                     | `v_series_temporal` (tipo=`clientes`)                                                                                                                                                          |                                      |
| Regional                                                  | `v_distribuicao_regional`                                                                                                                                                                      |                                      |
| Rankings (receita / ticket / qtd_pedidos / cluster)       | per-cliente rows                                                                                                                                                                               | `dim_clientes`                       |
| Detail dados_cadastrais                                   | `nome`, `cpf_cnpj`, `telefone`, `endereco_uf`, `endereco_cidade`                                                                                                                               | `dim_clientes`                       |
| Detail scorecards                                         | `receita_total`, `quantidade_total`, `total_pedidos`, `data_primeira_compra`, `data_ultima_compra`, `ticket_medio`, `frequencia_mensal`, `dias_recencia`, `pontuacao_cluster`, `nivel_cluster` | `dim_clientes`                       |
| Mix de produtos                                           | cross                                                                                                                                                                                          | RPC `get_client_top_products`        |

### 1.4 Fornecedores (analogous)

Same shape as clientes, keyed on `cnpj`. Columns read: `nome`, `cnpj`, `telefone`, `endereco_uf`, `endereco_cidade`, `receita_total`, `ticket_medio`, `total_pedidos_recebidos`, `frequencia_mensal`, `dias_recencia`, `data_primeira_transacao`, `data_ultima_transacao`, `pontuacao_cluster`, `nivel_cluster`.

### 1.5 Produtos (analogous)

Read from `dim_inventory` (aliased as "produtos" in UI): `nome`, `receita_total`, `quantidade_total_vendida`, `preco_medio`, `total_pedidos`, `quantidade_media_por_pedido`, `frequencia_mensal`, `dias_recencia`, `data_ultima_venda`, `pontuacao_cluster`, `nivel_cluster`.

### 1.6 Onboarding

**Zero reads** from `analytics_v2`. Writes only into `public` (auth, `client_data_sources`, agent config). Out of scope for this cleanup.

---

## Phase 2 — Target Minimal Schema

Five dimension tables + one fact table + four views + eight RPCs.

### 2.1 Dimensions (keep)

#### `analytics_v2.dim_clientes`

```
cliente_id            uuid PK
client_id             uuid        -- tenant
cpf_cnpj              text        -- natural key (unique with client_id)
nome                  text
telefone              text
endereco_uf           varchar(2)
endereco_cidade       text
-- Aggregates (refreshed by atualizar_agregados)
receita_total         numeric
quantidade_total      numeric
total_pedidos         integer
ticket_medio          numeric
frequencia_mensal     numeric
dias_recencia         integer
data_primeira_compra  date
data_ultima_compra    date
pontuacao_cluster     numeric
nivel_cluster         varchar(1)  -- A|B|C|D
atualizado_em         timestamptz
```

**Drop from current `dim_clientes`:** `endereco_rua`, `endereco_numero`, `endereco_bairro`, `endereco_cep`, `pedidos_ultimos_30_dias`, `criado_em`. (CEP only used by geoCluster — can be derived; if needed later, re-add.)

#### `analytics_v2.dim_fornecedores`

Mirror of `dim_clientes` with `cnpj` as natural key and `total_pedidos_recebidos`, `data_primeira_transacao`, `data_ultima_transacao`.

#### `analytics_v2.dim_inventory` (products)

```
inventory_id              uuid PK
client_id                 uuid
nome                      text        -- natural key with client_id
sku                       text NULL
-- Aggregates
receita_total             numeric
quantidade_total_vendida  numeric
preco_medio               numeric
total_pedidos             integer
quantidade_media_por_pedido numeric
frequencia_mensal         numeric
dias_recencia             integer
data_ultima_venda         date
pontuacao_cluster         numeric
nivel_cluster             varchar(1)
atualizado_em             timestamptz
```

**Drop:** `inventory_type`, `tracking_method`, `category_id`, `current_stock`, `minimum_stock`, `location` (hospitality/asset features not in v1 UI).

#### `analytics_v2.dim_datas`

Keep only: `data_id (int)`, `data`, `ano`, `trimestre`, `mes`, `nome_mes`, `semana_do_ano`, `dia`, `dia_da_semana`. Drop ISO/holiday flags and redundant bool columns.

#### `analytics_v2.dim_tipo_transacao` (keep as-is — tiny)

`tipo_id`, `nome`. Used to distinguish `venda` / `compra` / `devolução` if needed later.

### 2.2 Fact (slim)

#### `analytics_v2.fato_transacoes` — **minimum columns only**

```
transacao_id          uuid PK DEFAULT gen_random_uuid()
client_id             uuid NOT NULL
tipo_id               int  NOT NULL DEFAULT 0    -- FK dim_tipo_transacao
data_competencia_id   int  NOT NULL              -- FK dim_datas
cliente_id            uuid NULL  REFERENCES dim_clientes
fornecedor_id         uuid NULL  REFERENCES dim_fornecedores
inventory_id          uuid NULL  REFERENCES dim_inventory
documento             text NOT NULL              -- pedido/order number (grain = documento + linha)
linha                 int  NOT NULL DEFAULT 1
quantidade            numeric NOT NULL DEFAULT 0
valor_unitario        numeric
valor                 numeric NOT NULL DEFAULT 0 -- line total
status                text    NULL               -- completed|pending|cancelled
created_at            timestamptz DEFAULT now()
```

**Drop all 30+ invoice/NF/fiscal columns** (`nf_numero`, `danfe*`, `is_blocked`, `volume*`, `id_credito`, `data_credito`, `status_produto`, `was_purchased`, `was_compensation`, `compensations_ids`, `purchase_order_*`, `in_offer`, `has_credit`, `product_invalidations`, `cpl_adicional`, `fisco_adicional`, `danfe_materials`, `filial_*`, `movement_type`, `origem_tabela`, `origem_id`, `produto_id` duplicate of `inventory_id`, `categoria_id`, `data_efetiva_id`). Archive in a separate `analytics_v2_legacy.fato_transacoes_full` if historical data must be preserved.

Grain: **one row per order line** (`documento`, `linha`). Uniqueness enforced by `(client_id, documento, linha)`.

### 2.3 Views (keep 4, simplified)

| View                      | Purpose                      | Grain                                                  |
| ------------------------- | ---------------------------- | ------------------------------------------------------ |
| `v_resumo_dashboard`      | All HomePage KPIs in one row | 1 row per `client_id`                                  |
| `v_series_temporal`       | Time series for charts       | `(client_id, tipo_grafico, dimensao, periodo YYYY-MM)` |
| `v_distribuicao_regional` | Maps & regional rankings     | `(client_id, tipo_grafico, estado)`                    |
| `v_ultimos_pedidos`       | Latest 50 orders             | `(client_id, pedido_id)`                               |

**Drop:** `v_produtos_por_cliente`, `v_time_series`, `v_last_orders`, `v_customer_products`, `v_regional`, `erp_resumo_dashboard`, `erp_*` views, any other `v_*` not in the table above.

### 2.4 RPCs (keep 8)

Cross-entity top-N functions read by the detail modals:

- `get_client_top_products(p_client_name text)`
- `get_supplier_top_clients(p_supplier_name text)`
- `get_supplier_top_products(p_supplier_name text)`
- `get_supplier_top_regions(p_supplier_name text)`
- `get_supplier_revenue_series(p_supplier_name text)`
- `get_product_top_clients(p_product_name text)`
- `get_product_top_regions(p_product_name text)`
- `get_product_revenue_series(p_product_name text)`

**Drop all `erp_*` RPCs** not referenced by the dashboard or `standalone_agent_api` tool registry.

### 2.5 Tables to DROP

```
analytics_v2.dim_customer        -- legacy English
analytics_v2.clientes            -- legacy Portuguese-rename
analytics_v2.dim_supplier
analytics_v2.fornecedores
analytics_v2.dim_product
analytics_v2.produtos            -- superseded by dim_inventory
analytics_v2.dim_date
analytics_v2.datas
analytics_v2.fact_sales
analytics_v2.vendas
analytics_v2.fact_customer_product
analytics_v2.fact_reservations   -- hospitality Option B, not in v1 UI
analytics_v2.fact_availability
analytics_v2.dim_resources
analytics_v2.dim_categoria       -- only used by dropped current_stock flow
analytics_v2.erp_purchase_orders
analytics_v2.erp_purchase_order_items
analytics_v2.compras
```

---

## Phase 3 — Implementation Plan (Claude Opus Work Session)

### Phase A — Freeze current behavior

**Objective:** Snapshot data + create `analytics_v2_legacy` schema as fallback before any drops.
**Success criteria:** All current `analytics_v2` tables duplicated into `analytics_v2_legacy` via `CREATE TABLE ... AS SELECT ...`; `pg_dump` taken.

Tasks:

1. New migration `YYYYMMDD_snapshot_analytics_v2_legacy.sql`
   - `CREATE SCHEMA analytics_v2_legacy;`
   - For each table in the **DROP list**: `CREATE TABLE analytics_v2_legacy.<t> AS TABLE analytics_v2.<t>;`
   - Copy RLS policies (tenant isolation preserved).

### Phase B — Slim `fato_transacoes`

**Objective:** Drop 30+ unused invoice columns; keep the canonical 14-column grain defined in §2.2.
**Dependencies:** Phase A complete.

Tasks:

1. Migration `YYYYMMDD_slim_fato_transacoes.sql`:
   - `ALTER TABLE ... DROP COLUMN` for each column not in §2.2.
   - Drop `ON UPDATE` triggers that reference dropped columns.
   - Re-create unique index `(client_id, documento, linha)`.
   - Re-create partial indexes on `cliente_id`, `fornecedor_id`, `inventory_id`, `data_competencia_id`.
2. Regenerate [extract_bigquery_data](supabase/migrations/20260422170759_fix_fato_transacoes_required_column_fallbacks.sql#L1) fallbacks to reflect the new column set (only `tipo_id`, `data_competencia_id`, `valor`, `documento` remain mandatory).
3. Rewrite [multi_table_invoice_etl](supabase/migrations/20260422190000_multi_table_invoice_etl.sql) insert-section to populate only the minimal columns. Move invoice-specific fields into a new `analytics_v2_legacy.fato_transacoes_invoice_ext` table _only if_ polen project still needs them.

### Phase C — Consolidate dimensions

**Objective:** One Portuguese dim per entity. Drop all aliases.
**Dependencies:** Phase B complete and validated.

Tasks per dimension:

1. **dim_clientes:** drop columns per §2.1. Verify via grep that no code reads `endereco_rua|numero|bairro|cep|pedidos_ultimos_30_dias`. (CEP is only in geoCluster fallback — rewrite `getGeoClusters` to use `endereco_uf` exclusively.)
2. **dim_inventory:** drop hospitality/asset columns. Drop FK to `dim_categoria`. Drop `dim_categoria`.
3. **dim_datas:** drop ISO/weekend/month-boundary bool columns unless a view consumes them.
4. **Drop tables** from §2.5 one by one, each in its own migration to keep rollbacks trivial.

### Phase D — Rewrite views

**Objective:** Four views, each reading exclusively from the minimal schema.
**Dependencies:** Phase C complete.

Tasks:

1. `v_resumo_dashboard` — compute all HomePage scorecards inline from `fato_transacoes` + `dim_*` (columns listed in §1.1 + growth computed via `LAG() OVER (ORDER BY ano_mes)`).
2. `v_series_temporal` — expand axes via `tipo_grafico ∈ {pedidos, clientes, fornecedores, produtos, receita}` × `dimensao ∈ {total, contagem, receita, quantidade}`.
3. `v_distribuicao_regional` — `GROUP BY client_id, tipo_grafico, endereco_uf` (no city/CEP variants).
4. `v_ultimos_pedidos` — `ORDER BY data_transacao DESC LIMIT 50` per `client_id`, materialise with `ROW_NUMBER() AS ordem`.
5. Re-grant `SELECT` to `authenticated`; keep existing RLS `client_id = public.get_my_client_id()`.

### Phase E — Frontend verification

**Objective:** Dashboard boots on slim schema with zero runtime errors.
**Dependencies:** Phase D complete.

Tasks:

1. Run dashboard against a staging branch (`mcp_supabase_create_branch`).
2. Smoke-test the four pages: Home / Pedidos / Clientes / Fornecedores / Produtos.
3. Delete the fallbacks for removed columns in [analyticsService.ts](apps/vizu_dashboard/src/services/analyticsService.ts) (e.g., `endereco_cep` path in `getGeoClusters`).
4. Collapse `PedidoDetailResponse.dados_cliente.endereco` consumer to use `endereco_uf`/`endereco_cidade`.

### Phase F — Security & housekeeping

**Objective:** Pass `mcp_supabase_get_advisors` with zero errors.

Tasks:

1. Verify RLS policies exist on every remaining table (5 dims + 1 fact).
2. Drop unused functions flagged by `pg_stat_user_functions`.
3. Run `mcp_supabase_get_advisors(security)` and `(performance)`; fix issues.
4. Update repo memory: `/memories/repo/vizu-mono-architecture.md` with new schema diagram.

---

## Phase 4 — Risks & Considerations

### Technical considerations

- **Breaking change for `standalone_agent_api` / `atendente_core`:** their tool registry may reference dropped RPCs (`erp_*`). Grep and align before Phase E.
- **Polen / invoice project:** extensive `fato_transacoes` NF columns may still be required outside the dashboard. Solution: keep `analytics_v2_legacy` hot (read-only) and do not drop `analytics_v2_legacy` until polen migrates.
- **RLS:** policies must be re-created identically on new tables. Migration template: copy from [20260225_fix_analytics_v2_rls_policies.sql](supabase/migrations/20260225_fix_analytics_v2_rls_policies.sql).
- **Aggregate refresh:** `atualizar_agregados()` must be rewritten to target the slim `fato_transacoes`. Time series RPCs likewise.
- **Performance:** the main win is index footprint collapse on `fato_transacoes`. Expect query latency improvement on `v_resumo_dashboard` (currently reads wide rows).

### Non-goals (explicit)

- Reservations / availability (can return when hospitality vertical is promoted from onboarding `vertical=saude/servicos`).
- Product categories (`dim_categoria`) — re-add with the first feature that needs it.
- Address-level geo clustering — drop city/CEP until a map feature needs them.
- ERP purchase orders (`compras`) — deferred until a supply-planning dashboard exists.

---

## Phase 5 — GitHub Issues to Create (on approval)

Create in repo `CidLucas/platform`, project **Releases de produto**:

1. **[EPIC] analytics_v2 minimal schema cleanup** — tracking, labels: `epic`, `tracking`, `schema`.
2. **Phase A — Snapshot legacy schema** — labels: `phase-a`, `schema`, `data-safety`.
3. **Phase B — Slim fato_transacoes** — labels: `phase-b`, `schema`, `ingestion`. Depends on A.
4. **Phase C — Consolidate dimensions** — labels: `phase-c`, `schema`. Depends on B.
5. **Phase D — Rewrite 4 canonical views** — labels: `phase-d`, `schema`, `views`. Depends on C.
6. **Phase E — Frontend verification on staging branch** — labels: `phase-e`, `frontend`. Depends on D.
7. **Phase F — Security advisors + RLS audit** — labels: `phase-f`, `security`. Depends on E.

Each issue body should reference this plan document and contain the **Tasks** section from the corresponding phase above.
