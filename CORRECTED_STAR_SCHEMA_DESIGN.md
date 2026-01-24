# Corrected Star Schema Implementation

## Architecture Overview (FIXED)

### ✅ Correct Star Schema Design

```
DIMENSIONS (Contain Attributes + AGGREGATED Metrics)
├── dim_customer
│   ├── Attributes: name, cpf_cnpj, estado, etc.
│   └── Aggregates: total_orders, total_revenue, avg_order_value, frequency_per_month, recency_days
├── dim_supplier
│   ├── Attributes: name, emitter_cnpj, estado, etc.
│   └── Aggregates: total_orders_received, total_revenue, avg_order_value, frequency, recency
└── dim_product
    ├── Attributes: product_name, categoria, etc.
    └── Aggregates: total_quantity_sold, total_revenue, avg_price, number_of_orders, cluster_score

FACTS (Contain Transactional/Granular Data)
├── fact_sales (GRAIN: order_id + line_item_sequence)
│   ├── One row per order line item
│   ├── Contains: order_id, customer_cpf_cnpj, supplier_cnpj, product_name
│   └── Detailed: quantity, unit_price, line_total
│
└── fact_customer_product (GRAIN: customer + product)
    ├── One row per customer-product interaction
    ├── Bridge table showing which products each customer bought
    └── Aggregates: quantity_purchased, times_purchased, total_spent

MATERIALIZED VIEWS (Pre-computed for Performance)
├── mv_customer_summary: Customer metrics from fact_sales + dim_customer
├── mv_product_summary: Product metrics from fact_sales + dim_product
└── mv_monthly_sales_trend: Monthly aggregates from fact_sales
```

## What Changed (From Previous Implementation)

| Previous (❌ WRONG) | Current (✅ CORRECT) |
|-----|-----|
| fact_order_metrics = aggregated customer metrics | fact_sales = individual order line items |
| fact_product_metrics = aggregated product metrics | fact_customer_product = customer-product pairs |
| No aggregates in dimensions | dim_customer/product have total_orders, revenue, avg_price, etc. |
| Metrics hard-coded in separate tables | Metrics calculated via triggers/materialized views |

## New Data Flow

```
Raw Transaction Data (from data_ingestion_api)
        ↓
MetricService (ETL Processing)
        ↓
        ├──→ write_dim_customer()
        │     └── Dimensions: name, cpf_cnpj, estado, etc.
        │     └── Aggregates: SUM(orders), SUM(revenue), AVG(order_value)
        │
        ├──→ write_dim_supplier()
        │     └── Dimensions: name, emitter_cnpj, etc.
        │     └── Aggregates: SUM(orders_received), SUM(revenue)
        │
        ├──→ write_dim_product()
        │     └── Dimensions: product_name, category, etc.
        │     └── Aggregates: SUM(qty_sold), SUM(revenue), COUNT(orders)
        │
        ├──→ write_fact_sales() [TRANSACTIONAL]
        │     └── Individual order line items
        │     └── Grain: one row per product per order
        │     └── Contains: quantity, unit_price, line_total
        │
        ├──→ write_fact_customer_product() [BRIDGE]
        │     └── Customer-product interactions
        │     └── Aggregates per customer-product pair
        │
        └──→ Triggers Auto-Update Dimension Aggregates
              └── Every fact_sales insert updates dim_customer/product metrics
              └── Keep dimensions in sync with facts

↓ (On-demand or scheduled)

REFRESH MATERIALIZED VIEWS
├── mv_customer_summary (for dashboards)
├── mv_product_summary (for product analytics)
└── mv_monthly_sales_trend (for trend analysis)
```

## Implementation Steps

### Step 1: Update Dimension Write Methods

The current `write_star_customers()` should now populate aggregates:

```python
def write_dim_customer(self, client_id: str, customers_data: list[dict]) -> int:
    """Write customers with AGGREGATED order metrics to dim_customer"""
    # For each customer:
    # - name, cpf_cnpj, estado (from source)
    # - total_orders, total_revenue, avg_order_value (CALCULATED)
    # - frequency_per_month, recency_days (CALCULATED)
    # - lifetime_start_date, lifetime_end_date (MIN/MAX order dates)

    # These aggregates come from the ETL computation already in metric_service.py
    # Example: self.df_clientes_agg already has these computed
```

### Step 2: Create Transactional Fact Table Writes

Replace aggregate-based writes with transactional writes:

```python
def write_fact_sales(self, client_id: str, order_data: list[dict]) -> int:
    """Write individual order line items to fact_sales"""
    # Grain: one row per (order_id, line_item_sequence)
    # From raw data (self.df), not aggregated
    # Each row:
    #   order_id, line_item_sequence, quantity, unit_price, line_total

def write_fact_customer_product(self, client_id: str, customer_product_data: list[dict]) -> int:
    """Write customer-product pairs to bridge table"""
    # Grain: one row per (customer_cpf_cnpj, product_name)
    # Aggregates: quantity_purchased, times_purchased, total_spent
```

### Step 3: Implement Triggers

PostgreSQL triggers automatically update dimension aggregates when facts insert:

```sql
-- When a new fact_sales row is inserted:
-- 1. Calculate SUM(quantity) for that product → update dim_product
-- 2. Calculate COUNT(DISTINCT orders) for that customer → update dim_customer
-- 3. Calculate AVG(line_total) → update dimension averages
```

This keeps dimensions in sync without manual recalculation.

### Step 4: Refresh Materialized Views

Schedule periodic refreshes (e.g., nightly):

```python
# Call via API or scheduled job
SELECT analytics_v2.refresh_materialized_views();

# Or per-view:
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_customer_summary;
```

## Validation Endpoints (NEW)

### 1. Compare Old vs New Schemas

```bash
curl http://localhost:8000/api/debug/compare/{client_id}

Response:
{
  "comparison": {
    "old_schema": {"customers": 1624, "time_series": 960},
    "new_schema": {"customers": 1624, "fact_sales": 45000}
  },
  "schemas_match": true,
  "migration_status": "ready"
}
```

### 2. Validate Migration Completeness

```bash
curl http://localhost:8000/api/debug/validate/{client_id}

Response:
{
  "validation_checks": {
    "dim_customer_aggregates": {"valid": true, "customers_with_orders": 1624},
    "fact_sales_grain": {"valid": true, "fact_rows": 45000, "unique_orders": 8900},
    "materialized_views": {"valid": true, "views": {...}},
    "data_consistency": {"valid": true, "consistency_check": "10/10 customers match"}
  },
  "all_valid": true,
  "status": "✅ PASSED"
}
```

### 3. Get Schema Metrics

```bash
curl http://localhost:8000/api/debug/metrics/{client_id}

Response:
{
  "dimensions": {
    "customers": {"row_count": 1624, "status": "✅"},
    "products": {"row_count": 1150, "status": "✅"}
  },
  "facts": {
    "fact_sales": {"row_count": 45000, "status": "✅"},
    "fact_customer_product": {"row_count": 11891, "status": "✅"}
  },
  "materialized_views": {...}
}
```

## Testing Strategy

### Test 1: Side-by-Side Comparison

```bash
# Old schema query
curl http://localhost:8000/api/dashboard/summary/{client_id}  # Gold tables

# New schema query
curl http://localhost:8000/api/v2/dashboard/summary/{client_id}  # V2 tables

# Comparison
curl http://localhost:8000/api/debug/compare/{client_id}
# Should show matching row counts and values
```

### Test 2: Transactional Data Integrity

```sql
-- Verify facts sum correctly to dimensions
SELECT
  d.customer_id,
  d.total_orders,  -- from dimension
  COUNT(DISTINCT f.order_id) as fact_count,  -- calculated from facts
  (d.total_orders = COUNT(DISTINCT f.order_id)) as match
FROM dim_customer d
LEFT JOIN fact_sales f ON d.cpf_cnpj = f.customer_cpf_cnpj
GROUP BY d.customer_id, d.total_orders
HAVING d.total_orders != COUNT(DISTINCT f.order_id);
-- Should return ZERO mismatches
```

### Test 3: Materialized View Performance

```bash
# Monitor view refresh time
SELECT analytics_v2.refresh_materialized_views();

# Check view is up-to-date
SELECT COUNT(*) FROM analytics_v2.mv_customer_summary WHERE client_id = '...';
```

## Deployment Checklist

- [ ] Deploy SQL migration to create:
  - [ ] New columns in dim_* tables for aggregates
  - [ ] fact_sales table (transactional)
  - [ ] fact_customer_product table (bridge)
  - [ ] Materialized views
  - [ ] Triggers for auto-aggregate updates
  - [ ] Refresh function

- [ ] Update ETL code to:
  - [ ] Populate dimension aggregates properly
  - [ ] Write transactional data to fact_sales (not aggregated)
  - [ ] Write customer-product pairs to fact_customer_product

- [ ] Deploy comparison/validation endpoints

- [ ] Test side-by-side:
  - [ ] Old vs new schemas match
  - [ ] Fact sums equal dimension aggregates
  - [ ] Materialized views are current

- [ ] Schedule materialized view refreshes (e.g., nightly job)

- [ ] Monitor logs for trigger/view performance

## Key Differences: Proper vs Improper Star Schema

| Aspect | ❌ Improper | ✅ Proper |
|--------|-----------|---------|
| Aggregates location | In fact tables | In dimension tables |
| Fact table grain | Mixed (sometimes aggregated, sometimes detailed) | Consistent (always transactional) |
| Dimensions | Dimensions are flat, no metrics | Dimensions include calculated aggregates |
| Updates | Manual recalculation of aggregates | Automatic via triggers |
| Query performance | Need to join fact→dimension to get metrics | Direct access from dimension row |
| Data consistency | Risk of mismatch between fact and dimension | Guaranteed consistency via triggers |

## Benefits of Corrected Architecture

1. **Better Performance**: Queries can read aggregates from dimensions without joining facts
2. **Easier Maintenance**: Triggers keep dimensions in sync automatically
3. **Cleaner Design**: Proper separation of concerns (dims=attributes+aggregates, facts=transactions)
4. **Standards Compliant**: Follows Kimball star schema best practices
5. **Scalability**: Materialized views handle heavy queries without hitting base tables

---

**Status**: Architecture documented and ready for implementation
**Next Step**: Run migration and update ETL code to follow proper star schema pattern
