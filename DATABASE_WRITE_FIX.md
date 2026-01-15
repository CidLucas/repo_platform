# Database Write Fix - Complete Solution

## Problem Diagnosis

**Reported Issue:**
All ranking columns in Supabase gold tables showing zeros or NULLs:
- quantidade_total → 0
- num_pedidos_unicos → 0
- ticket_medio → 0
- quantidade_media_por_pedido → 0
- frequencia_pedidos_mes → 0
- recencia_dias → 0
- valor_unitario_medio → 0
- cluster_score → 0
- cluster_tier → NULL
- primeira_venda → NULL
- ultima_venda → NULL

**Root Cause:**
The write methods in `postgres_repository.py` were **NOT writing to the new ranking columns** added by migration `20260109_enhance_gold_tables_with_ranking_fields.sql`.

The INSERT statements only targeted the **old basic columns**:
- customers: `total_orders`, `lifetime_value`, `avg_order_value`, `first_order_date`, `last_order_date`
- suppliers: `total_orders`, `total_revenue`, `avg_order_value`, `unique_products`
- products: `total_quantity_sold`, `total_revenue`, `avg_price`, `order_count`

But the migration added **11 new ranking columns** that were never being populated.

---

## Solution Applied

### 1. Fixed recencia_dias Calculation ✅

**File:** [metric_service.py:208-221](services/analytics_api/src/analytics_api/services/metric_service.py)

Changed from "days since last purchase" to **"average days between consecutive transactions"**:

```python
def calculate_avg_days_between_orders(entity_name):
    entity_df = df[df[dimension_col] == entity_name].sort_values('data_transacao')
    if len(entity_df) <= 1:
        return 0  # No interval to calculate
    # Calculate intervals between consecutive transactions
    intervals = entity_df['data_transacao'].diff().dt.days.dropna()
    return intervals.mean() if len(intervals) > 0 else 0

agg_df['recencia_dias'] = agg_df[dimension_col].apply(calculate_avg_days_between_orders)
```

### 2. Added period_start and period_end ✅

**File:** [metric_service.py:199-201](services/analytics_api/src/analytics_api/services/metric_service.py)

```python
agg_df['period_start'] = agg_df['primeira_venda']
agg_df['period_end'] = agg_df['ultima_venda']
```

### 3. Updated write_gold_customers() ✅

**File:** [postgres_repository.py:470-521](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)

**Before:** Writing only 12 columns (old schema)
**After:** Writing 23 columns (old + new ranking fields)

```sql
INSERT INTO analytics_gold_customers (
    client_id, customer_name, customer_cpf_cnpj,
    total_orders, lifetime_value, avg_order_value,
    first_order_date, last_order_date, customer_type, period_type,
    period_start, period_end,
    -- NEW: All ranking columns
    quantidade_total, num_pedidos_unicos, ticket_medio, qtd_media_por_pedido,
    frequencia_pedidos_mes, recencia_dias, valor_unitario_medio,
    cluster_score, cluster_tier, primeira_venda, ultima_venda,
    calculated_at, created_at, updated_at
) VALUES ...
```

### 4. Updated write_gold_suppliers() ✅

**File:** [postgres_repository.py:542-590](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)

**Before:** Writing only 10 columns
**After:** Writing 21 columns

```sql
INSERT INTO analytics_gold_suppliers (
    client_id, supplier_name, supplier_cnpj,
    total_orders, total_revenue, avg_order_value, unique_products, period_type,
    period_start, period_end,
    -- NEW: All ranking columns
    quantidade_total, num_pedidos_unicos, ticket_medio, qtd_media_por_pedido,
    frequencia_pedidos_mes, recencia_dias, valor_unitario_medio,
    cluster_score, cluster_tier, primeira_venda, ultima_venda,
    calculated_at, created_at, updated_at
) VALUES ...
```

### 5. Updated write_gold_products() ✅

**File:** [postgres_repository.py:611-657](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)

**Before:** Writing only 9 columns
**After:** Writing 19 columns

```sql
INSERT INTO analytics_gold_products (
    client_id, product_name,
    total_quantity_sold, total_revenue, avg_price, order_count, period_type,
    period_start, period_end,
    -- NEW: All ranking columns
    quantidade_total, num_pedidos_unicos, ticket_medio, qtd_media_por_pedido,
    frequencia_pedidos_mes, recencia_dias,
    cluster_score, cluster_tier, primeira_venda, ultima_venda,
    calculated_at, created_at, updated_at
) VALUES ...
```

---

## Expected Database Values After Fix

### Customers (analytics_gold_customers)

| Column | Expected Value | Example |
|--------|----------------|---------|
| quantidade_total | Total quantity purchased | 271.88 |
| num_pedidos_unicos | Count of unique orders | 10 |
| ticket_medio | receita / num_pedidos | 7,597.92 |
| qtd_media_por_pedido | quantidade / num_pedidos | 27.79 |
| frequencia_pedidos_mes | Orders per month | 4.14 |
| recencia_dias | Avg days between orders | 9 (not 0!) |
| valor_unitario_medio | Average unit price | 263.13 |
| cluster_score | RFM combined score (0-100) | 45.23 |
| cluster_tier | Segment (A/B/C/D) | "A (Melhores)" |
| primeira_venda | First purchase date | 2025-10-15T10:30:00Z |
| ultima_venda | Last purchase date | 2026-01-14T14:20:00Z |

### Suppliers (analytics_gold_suppliers)

| Column | Expected Value | Example |
|--------|----------------|---------|
| quantidade_total | Total quantity supplied | 906.25 |
| num_pedidos_unicos | Count of unique orders | 33 |
| ticket_medio | receita / num_pedidos | 7,392.39 |
| qtd_media_por_pedido | quantidade / num_pedidos | 27.20 |
| frequencia_pedidos_mes | Orders per month | 11.91 |
| recencia_dias | Avg days between orders | 2.64 |
| valor_unitario_medio | Average unit price | 261.55 |
| cluster_score | RFM combined score | 85.67 |
| cluster_tier | Segment | "A (Melhores)" |

### Products (analytics_gold_products)

| Column | Expected Value | Example |
|--------|----------------|---------|
| quantidade_total | Total quantity sold | 181.25 |
| num_pedidos_unicos | Count of orders | 6 |
| ticket_medio | receita / num_pedidos | 7,025.63 |
| qtd_media_por_pedido | quantidade / num_pedidos | 26.69 |
| frequencia_pedidos_mes | Sales per month | 3.30 |
| recencia_dias | Avg days between sales | 11.61 |
| cluster_score | Performance score | 62.15 |
| cluster_tier | Product tier | "B" |

---

## Key Differences: Old vs New Columns

### Backwards Compatibility Maintained

Both **old** and **new** columns are now populated with the same data:

| Old Column | New Column | Value Mapping |
|------------|------------|---------------|
| total_orders | num_pedidos_unicos | Same value (both get num_pedidos_unicos) |
| lifetime_value | receita_total | Same value (both get receita_total) |
| avg_order_value | ticket_medio | Same value (both get ticket_medio) |
| first_order_date | primeira_venda | Same value |
| last_order_date | ultima_venda | Same value |
| customer_type | cluster_tier | Same value |

This dual-write ensures:
1. ✅ Old frontend code using old columns still works
2. ✅ New frontend code using new columns gets full metrics
3. ✅ No breaking changes to existing queries

---

## Validation Steps

### 1. Verify Migration Was Run

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'analytics_gold_customers'
  AND column_name IN (
    'quantidade_total', 'num_pedidos_unicos', 'ticket_medio',
    'qtd_media_por_pedido', 'frequencia_pedidos_mes', 'recencia_dias',
    'valor_unitario_medio', 'cluster_score', 'cluster_tier',
    'primeira_venda', 'ultima_venda'
  )
ORDER BY ordinal_position;
```

**Expected:** 11 rows showing all new columns exist

### 2. Check Current Data

```sql
SELECT
  customer_name,
  num_pedidos_unicos,
  ticket_medio,
  recencia_dias,
  cluster_tier,
  primeira_venda,
  ultima_venda
FROM analytics_gold_customers
WHERE client_id = 'your-client-id'
LIMIT 5;
```

**Expected BEFORE fix:** All zeros/NULLs
**Expected AFTER fix:** Actual numeric values and dates

### 3. Re-process Data

After deploying the code fix, trigger a data re-process:
1. Call the Analytics API ingestion endpoint
2. Or manually trigger `MetricService(repo, client_id, write_gold=True)`

---

## Deployment Checklist

- [x] Fix recencia_dias calculation logic
- [x] Add period_start/period_end columns to aggregations
- [x] Update write_gold_customers() to write all 23 columns
- [x] Update write_gold_suppliers() to write all 21 columns
- [x] Update write_gold_products() to write all 19 columns
- [ ] **Deploy updated code to production**
- [ ] **Verify migration `20260109_enhance_gold_tables_with_ranking_fields.sql` was run**
- [ ] **Re-process existing client data to populate new columns**
- [ ] **Verify data in Supabase (no more zeros/NULLs)**
- [ ] **Update frontend to use new ranking columns**

---

## Files Modified

1. **[metric_service.py](services/analytics_api/src/analytics_api/services/metric_service.py)**
   - Lines 146-230: Fixed recencia_dias, added period columns

2. **[postgres_repository.py](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)**
   - Lines 470-521: Updated write_gold_customers()
   - Lines 542-590: Updated write_gold_suppliers()
   - Lines 611-657: Updated write_gold_products()

---

## Test Results

All tests passing with realistic data:
- ✅ Customers: 10 records with full metrics
- ✅ Suppliers: 3 records with full metrics
- ✅ Products: 15 records with full metrics
- ✅ NO zeros in financial columns
- ✅ NO NULLs in date columns
- ✅ recencia_dias now shows meaningful intervals (not zeros)

See test output: [test_metric_service.py](test_metric_service.py) - All 9 steps passing
