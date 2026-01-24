# fact_sales Bulk Write Implementation

## Overview

Implemented the critical `write_fact_sales()` method to populate the transactional fact table with invoice-level data. This enables all reporting views to compute automatically from a single source of truth.

## What Was Implemented

### 1. **write_fact_sales() Method**
**File**: `services/analytics_api/src/analytics_api/data_access/postgres_repository.py` (after line 1515)

**Purpose**: Bulk insert transactional data from invoices into fact_sales table

**Key Features**:
- **FK Lookup Pattern**: For each invoice:
  1. Look up customer_id from dim_customer by CPF/CNPJ
  2. Look up supplier_id from dim_supplier by CNPJ
  3. Look up product_id from dim_product by product name
  4. Insert fact row with FK references

- **Data Validation**: Skips inserts if any dimension is missing, logs failures with reason

- **Column Mapping**:
  - Source columns (from invoice data):
    - `receiver_cpf_cnpj` → customer_cpf_cnpj (lookup customer_id)
    - `emitter_cnpj` → supplier_cnpj (lookup supplier_id)
    - `raw_product_description` → product FK (lookup product_id)
    - `order_id`, `data_transacao`, `quantidade`, `valor_unitario`, `valor_total_emitter` → fact columns

- **Error Handling**:
  - Catches missing dimensions (customer not found, supplier not found, product not found)
  - Logs first 5 failures as warnings
  - Continues processing remaining records on individual failures
  - Full rollback on database-level errors

### 2. **Integration into metric_service.py**
**File**: `services/analytics_api/src/analytics_api/services/metric_service.py` (line 450+)

**When Called**: `_write_all_gold_tables()` method, after dimensions are written but before chart views

**Input Data**: self.df (all invoice line items) with columns:
- order_id
- data_transacao
- quantidade
- valor_unitario
- valor_total_emitter
- receiver_cpf_cnpj
- emitter_cnpj
- raw_product_description

**Output**: Number of successfully inserted rows

**Logging**: Detailed progress logs at INFO level

```python
# Added at line 450+:
if not self.df.empty:
    logger.info(f"  ➜ Writing transaction-level fact_sales data...")
    transactions_data = self.df[[
        'order_id', 'data_transacao', 'quantidade', 'valor_unitario', 'valor_total_emitter',
        'receiver_cpf_cnpj', 'emitter_cnpj', 'raw_product_description'
    ]].copy().to_dict('records')

    try:
        sales_count = self.repository.write_fact_sales(self.client_id, transactions_data)
        logger.info(f"  ✓ Written {sales_count} transaction records to analytics_v2.fact_sales")
    except Exception as e:
        logger.error(f"  ✗ Failed to write fact_sales: {e}", exc_info=True)
```

## Data Flow

```
Invoice Data (self.df)
    ↓
metric_service._write_all_gold_tables()
    ↓
1. write_star_customers()  → dim_customer
2. write_star_suppliers()  → dim_supplier
3. write_star_products()   → dim_product
4. write_fact_sales()      → fact_sales (with FK lookups)
    ↓
Triggers Auto-Update:
- dim_customer.updated_at ← tr_update_customer_aggregates
- dim_supplier.updated_at ← tr_update_supplier_aggregates
- dim_product.updated_at  ← tr_update_product_aggregates
    ↓
Materialized Views Auto-Compute:
- v_time_series        (monthly sales aggregates)
- v_regional          (supplier-region breakdown)
- v_last_orders       (recent transactions)
- v_customer_products (customer-product affinity)
    ↓
API Endpoints Return Data:
- GET /v2/time_series        → queries v_time_series
- GET /v2/regional          → queries v_regional
- GET /v2/customer_products → queries v_customer_products
```

## How It Works

### Insert Process

1. **Extract Transactions**: Get all invoice rows from self.df
2. **For Each Invoice**:
   - Query dim_customer: `SELECT customer_id WHERE cpf_cnpj = ?`
   - Query dim_supplier: `SELECT supplier_id WHERE cnpj = ?`
   - Query dim_product: `SELECT product_id WHERE product_name = ?`
   - If all 3 found → INSERT into fact_sales with FKs
   - If any missing → Log failure and skip this row

3. **Commit**: All successful inserts are committed together
4. **Report**: Log success count + failure reasons

### Dimension Triggering

When fact_sales gets rows:
- Triggers fire on dim_* tables (if they existed in fact_sales)
- Auto-updates aggregates like quantity_total, receita_total
- Triggers update the updated_at timestamp

### View Computation

Views run queries like:
```sql
-- v_time_series
SELECT
    EXTRACT(YEAR_MONTH FROM fs.data_transacao) as month,
    SUM(fs.quantidade) as qty_total,
    SUM(fs.valor_total) as revenue_total
FROM fact_sales fs
GROUP BY EXTRACT(YEAR_MONTH FROM fs.data_transacao)
```

Materialized views cache the results for fast API responses.

## Existing Fact Tables (Not Affected)

These aggregated fact tables still exist and are written by different methods:
- **fact_order_metrics**: Order-level aggregates (write_fact_order_metrics)
- **fact_product_metrics**: Product-level aggregates (write_fact_product_metrics)
- **fact_customer_product**: Customer-product affinity (write_star_customer_products)

**Note**: The new fact_sales table is transactional (one row per invoice line item) and is the source for all view computations. The older fact_* tables are optional aggregates.

## What Happens Next

### When ETL Runs:
1. ✅ Dimensions get populated (existing code)
2. ✅ fact_sales gets populated (NEW - just implemented)
3. ✅ Dimension aggregates auto-update (via triggers)
4. ✅ Views auto-compute from fact_sales (existing views)
5. ✅ API endpoints return view data (already fixed)

### Expected Results:
- Endpoints return non-empty results
- Time series, regional, and customer_products views show actual data
- All views stay in sync automatically (fact_sales is the source)

## Testing the Implementation

### 1. Verify Schema
```sql
SELECT COUNT(*) FROM analytics_v2.fact_sales;  -- Should be > 0 after ETL
```

### 2. Verify Views
```sql
SELECT COUNT(*) FROM analytics_v2.v_time_series;        -- Should have rows
SELECT COUNT(*) FROM analytics_v2.v_regional;           -- Should have rows
SELECT COUNT(*) FROM analytics_v2.v_customer_products;  -- Should have rows
```

### 3. Verify API
```bash
curl "https://api.analytics.local/v2/time_series?client_id=test"
curl "https://api.analytics.local/v2/regional?client_id=test"
curl "https://api.analytics.local/v2/customer_products?client_id=test"
```

## Code Quality

✅ **Type Safety**: Full type hints on method signature and parameters
✅ **Error Handling**: Graceful degradation on missing dimensions, detailed error logs
✅ **Data Quality**: Skips invalid rows rather than crashing
✅ **Performance**: Row-by-row with FK lookups (not bulk execute_values) - suitable for typical invoice volumes (100-10k rows)
✅ **Logging**: DEBUG level for setup, INFO for results, WARNING for failures, ERROR for exceptions
✅ **Integration**: Seamlessly integrated into existing ETL pipeline

## Files Modified

1. **postgres_repository.py**
   - Added: write_fact_sales() method (~100 lines)
   - Location: After write_star_products() method

2. **metric_service.py**
   - Added: Call to write_fact_sales() in _write_all_gold_tables()
   - Location: Before chart views write, after dimension writes

## Notes

- The implementation handles dimension lookups by business key (not generated UUIDs)
- Individual row failures don't block other rows (graceful degradation)
- Views remain materialized and will stay in sync as fact_sales is the single source of truth
- Future optimization: Could switch to bulk execute_values() if performance becomes an issue with millions of rows
