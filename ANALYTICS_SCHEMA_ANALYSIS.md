# Analytics Schema Analysis & Cleanup Plan

**Date:** 2026-02-03
**Purpose:** Document current schema, identify duplication, and plan cleanup

---

## Current Analytics_v2 Schema

### Core Tables (Star Schema)

| Table | Purpose | Row Count Estimate | Key Columns |
|-------|---------|-------------------|-------------|
| `fact_sales` | Transaction facts (grain: 1 row per line item) | ~millions | `order_id`, `customer_cpf_cnpj`, `supplier_cnpj`, `product_name`, `line_total`, `quantity`, `order_date` |
| `dim_customer` | Customer dimensions + aggregates | ~thousands | `customer_id`, `cpf_cnpj`, `name`, `estado`, `receita_total`, `ticket_medio`, `cluster_tier` |
| `dim_supplier` | Supplier dimensions + aggregates | ~hundreds | `supplier_id`, `cnpj`, `name`, `receita_total` |
| `dim_product` | Product dimensions + aggregates | ~thousands | `product_id`, `product_name`, `receita_total`, `quantidade_total` |
| `dim_time` | Date dimension (unused currently) | 0 | N/A |
| `fact_customer_product` | Customer-product bridge (unused) | 0 | N/A |

**Aggregates stored in dimension tables:**
- `receita_total`, `quantidade_total`, `ticket_medio`
- `frequencia_pedidos_mes`, `recencia_dias`
- `cluster_score`, `cluster_tier` (RFM scoring)
- `num_pedidos_unicos`, `primeira_venda`, `ultima_venda`

---

### Materialized Views (Performance Layer)

| View | Purpose | Source | Refresh Strategy | Status |
|------|---------|--------|------------------|--------|
| `mv_customer_summary` | Pre-aggregated customer metrics (SUBSET of dim_customer) | Joins `dim_customer` + `fact_sales` | Manual CONCURRENT refresh after ingestion | ⚠️ **REDUNDANT** - dim_customer has same data + more (contact info, RFM scores) |
| `mv_product_summary` | Pre-aggregated product metrics | Joins `dim_product` + `fact_sales` | Manual CONCURRENT refresh | ✅ Keep - used for dashboard queries |
| `mv_monthly_sales_trend` | Monthly time-series aggregates | Aggregates `fact_sales` by month | Manual CONCURRENT refresh | ✅ Keep - useful for time-series charts |

**mv_customer_summary Columns:**
- client_id, customer_id, name, cpf_cnpj
- total_orders, lifetime_value, avg_order_value, total_quantity
- last_order_date, first_order_date

**dim_customer Has Everything Above PLUS:**
- Contact info: telefone, endereco_*
- Advanced metrics: frequency_per_month, recency_days, orders_last_30_days
- RFM/clustering: cluster_score, cluster_tier (NOT in MV)

**Recommendation:**
- ❌ **DROP mv_customer_summary** - it's a subset of dim_customer
- Query dim_customer directly instead (has all the same data + more)
- Keep mv_product_summary and mv_monthly_sales_trend
- Ensure MVs are refreshed after every ingestion

---

### Computed Views (Exist and Working)

The following views **exist in the database** and provide real-time aggregations:

| View | Purpose | Status |
|------|---------|--------|
| `v_time_series` | Time-series aggregations for charts (monthly trends) | ✅ **EXISTS** |
| `v_regional` | Regional breakdowns by state | ✅ **EXISTS** |
| `v_last_orders` | Most recent transactions | ✅ **EXISTS** |
| `v_customer_products` | Customer purchase history by product | ✅ **EXISTS** |

**Current Status:**
- Code correctly queries these views via `postgres_repository.read_star_*()` methods
- Views aggregate from `fact_sales` on-the-fly
- No materialization needed (queries are fast enough)

✅ **No action required** - views are working as designed

---

## Data Quality / Admin Views

| View | Purpose | Usage |
|------|---------|-------|
| `v_customers_missing_contact` | Find customers with NULL phone/address | Data quality checks |
| `v_duplicate_customer_records` | Detect duplicate CPF/CNPJ entries | Data cleanup |
| `v_column_consistency_check` | Verify column mappings across clients | Schema validation |

✅ **Keep — useful for troubleshooting**

---

## Duplication & Redundancy Issues

### Issue #1: Dual Computation Path (Addressed in Phase 2)

**Current flow:**
1. Pandas computes aggregates → stores in `df_clientes_agg`, `df_fornecedores_agg`, `df_produtos_agg`
2. Writes these pandas-computed values to `dim_customer`, `dim_supplier`, `dim_product`
3. **Then** SQL UPDATEs recompute THE SAME metrics from `fact_sales`

**Impact:** 30-40% slower ingestion, redundant computation

**Fix (Phase 2):**
- Remove pandas aggregation (keep only dimension extraction: names, IDs)
- Write skeleton dimension records (just IDs/names, NULL metrics)
- Let SQL populate ALL metrics from `fact_sales` (single source of truth)

### Issue #2: Missing Views Referenced in Code

**Current behavior:**
```python
# postgres_repository.py line 954
def read_star_time_series(...):
    """Retrieve time-series chart data from v_time_series view..."""
    # ❌ This view doesn't exist!
```

**Impact:** Frontend charts may be broken or empty

**Fix (Phase 3 - Part B):**
Create missing views OR rewrite methods to query dimension tables directly.

### Issue #3: Unused Tables

| Table | Status | Recommendation |
|-------|--------|----------------|
| `dim_time` | Empty, never populated | ❌ **DROP** — time-series uses `fact_sales.order_date` directly |
| `fact_customer_product` | Empty, superseded by views | ❌ **DROP** — data available via `v_customer_products` (when created) |

---

## Frontend Usage Analysis

### What the Frontend Currently Expects

Based on `postgres_repository.py` methods called by `metric_service.py`:

| Endpoint | Data Source | View/Table Used |
|----------|-------------|-----------------|
| Home Dashboard | `get_home_scorecards_and_metrics()` | `dim_customer`, `dim_supplier`, `dim_product`, `fact_sales` |
| Fornecedores Overview | `get_fornecedores_overview()` | `dim_supplier`, `mv_product_summary` (fallback to `dim_product`) |
| Clientes Overview | `get_clientes_overview()` | `dim_customer`, `mv_customer_summary` (fallback) |
| Produtos Overview | `get_produtos_overview()` | `dim_product`, `mv_product_summary` (fallback) |
| Pedidos Overview | `get_pedidos_overview()` | `fact_sales` directly |
| Time-Series Charts | `read_star_time_series()` | ❌ `v_time_series` (MISSING) |
| Regional Breakdown | `read_star_regional()` | ❌ `v_regional` (MISSING) |
| Last Orders | `read_star_last_orders()` | ❌ `v_last_orders` (MISSING) |
| Customer Products | `read_star_customer_products()` | ❌ `v_customer_products` (MISSING) |

**Critical Finding:** Frontend likely has broken charts due to missing views.

---

## Schema Cleanup Roadmap

### Phase 3A: Document Current State ✅ (This Document)

### Phase 3B: Create Missing Views (HIGH PRIORITY)

**Create SQL views:**

```sql
-- v_time_series: Monthly aggregates for line charts
CREATE OR REPLACE VIEW analytics_v2.v_time_series AS
SELECT
    client_id,
    'fornecedores_tempo' as chart_type,
    DATE_TRUNC('month', order_date)::DATE as label,
    COUNT(DISTINCT supplier_cnpj) as value
FROM analytics_v2.fact_sales
GROUP BY client_id, DATE_TRUNC('month', order_date)::DATE
UNION ALL
SELECT
    client_id,
    'clientes_tempo' as chart_type,
    DATE_TRUNC('month', order_date)::DATE as label,
    COUNT(DISTINCT customer_cpf_cnpj) as value
FROM analytics_v2.fact_sales
GROUP BY client_id, DATE_TRUNC('month', order_date)::DATE
-- ... (add remaining chart types)
;

-- v_regional: State-level aggregates
CREATE OR REPLACE VIEW analytics_v2.v_regional AS
SELECT
    f.client_id,
    'fornecedores_regiao' as chart_type,
    s.estado as label,
    COUNT(DISTINCT s.supplier_id) as value
FROM analytics_v2.fact_sales f
JOIN analytics_v2.dim_supplier s ON f.supplier_cnpj = s.cnpj AND f.client_id = s.client_id
GROUP BY f.client_id, s.estado
-- ... (add clientes, pedidos)
;

-- v_last_orders: Most recent transactions
CREATE OR REPLACE VIEW analytics_v2.v_last_orders AS
SELECT
    f.client_id,
    f.order_id,
    f.order_date,
    c.name as customer_name,
    f.line_total,
    f.quantity
FROM analytics_v2.fact_sales f
JOIN analytics_v2.dim_customer c ON f.customer_cpf_cnpj = c.cpf_cnpj AND f.client_id = c.client_id
ORDER BY f.order_date DESC
LIMIT 100;

-- v_customer_products: Customer purchase history
CREATE OR REPLACE VIEW analytics_v2.v_customer_products AS
SELECT
    f.client_id,
    f.customer_cpf_cnpj,
    f.product_name,
    SUM(f.quantity) as total_quantity,
    SUM(f.line_total) as total_spent,
    MAX(f.order_date) as last_purchase_date
FROM analytics_v2.fact_sales f
GROUP BY f.client_id, f.customer_cpf_cnpj, f.product_name;
```

### Phase 3C: Drop Unused Tables (LATER)

After confirming views work:
- Drop `dim_time` (never used)
- Drop `fact_customer_product` (superseded by views)

### Phase 3D: Consolidate Redundant Columns (FUTURE)

Some dimension tables have redundant columns that could be computed on-the-fly from `fact_sales`:
- Consider storing only IDs/names in dimensions
- Compute ALL aggregates via views/MVs
- **Trade-off:** Faster writes, slower reads (mitigated by MVs)

---

## Testing Checklist

Before deploying schema changes:

- [ ] Create missing views in staging environment
- [ ] Run full ingestion → verify MVs refresh correctly
- [ ] Test frontend dashboard → confirm charts display
- [ ] Check MV staleness logic → ensure WARNING logs appear
- [ ] Performance test: compare query times (views vs direct fact_sales queries)
- [ ] Verify RLS policies apply to new views

---

## Next Actions

1. **Immediate (High Priority):**
   - Create missing views (`v_time_series`, `v_regional`, `v_last_orders`, `v_customer_products`)
   - Add MV staleness check to `postgres_repository.py`
   - Ensure MV refresh runs after every ingestion

2. **Phase 2 (Performance):**
   - Remove pandas aggregation (see separate plan)
   - SQL-only aggregation path

3. **Future Cleanup:**
   - Drop `dim_time` and `fact_customer_product` tables
   - Consider moving dimension aggregates to MVs entirely

---

**Document Owner:** GitHub Copilot
**Last Updated:** 2026-02-03
**Status:** DRAFT — Requires review + view creation
