# PostgreSQL Repository Cleanup Plan

**Current State**: 2,415 lines with significant technical debt

## Summary of Changes

### REMOVING (Old Gold Schema - Deprecated)

**Write Methods to Remove**:
- ❌ `write_gold_customers()` - Replaced by write_star_customers()
- ❌ `write_gold_suppliers()` - Replaced by write_star_suppliers()
- ❌ `write_gold_products()` - Replaced by write_star_products()
- ❌ `write_gold_customer_products()` - Replaced by write_star_customer_products()
- ❌ `write_gold_orders_bulk()` - Replaced by fact_sales
- ❌ `write_gold_orders()` - Legacy wrapper, redundant
- ❌ `write_gold_time_series()` - Replaced by views
- ❌ `write_gold_regional()` - Replaced by views
- ❌ `write_gold_last_orders()` - Replaced by views

**Read Methods to Remove**:
- ❌ `get_gold_orders_metrics()` - Use get_v2_time_series()
- ❌ `get_gold_orders_time_series()` - Use get_v2_time_series()
- ❌ `get_gold_products_metrics()` - Use views directly
- ❌ `get_gold_customers_metrics()` - Use views directly
- ❌ `get_gold_suppliers_metrics()` - Use views directly
- ❌ `get_gold_customer_products()` - Use get_v2_customer_products()
- ❌ `get_gold_time_series()` - Use get_v2_time_series()
- ❌ `get_gold_time_series_with_dates()` - Use views directly
- ❌ `get_gold_products_aggregated()` - Redundant
- ❌ `get_gold_customers_aggregated()` - Redundant
- ❌ `get_gold_regional()` - Use get_v2_regional()
- ❌ `get_gold_last_orders()` - Use get_v2_last_orders()

**Non-existent Table Methods to Remove**:
- ❌ `write_fact_order_metrics()` - Table doesn't exist
- ❌ `write_fact_product_metrics()` - Table doesn't exist

**Helper Methods to Remove**:
- ❌ `_get_gold_table_single()` - Only used by gold methods
- ❌ `_get_gold_table_multiple()` - Only used by gold methods
- ❌ `_get_period_date_range()` - Only used by gold methods
- ❌ `get_order_metrics_by_date_range()` - Old pattern
- ❌ `get_product_metrics_by_date_range()` - Old pattern
- ❌ `get_customer_metrics_by_date_range()` - Old pattern
- ❌ `get_products_by_customer_cpf_cnpj()` - Redundant with v2 version
- ❌ `get_distinct_products()` - Unused helper
- ❌ `get_distinct_customers()` - Unused helper
- ❌ `calculate_growth_from_time_series()` - Complex metric, not used
- ❌ `get_comparison_metrics_from_time_series()` - Complex, unused
- ❌ `get_all_comparison_metrics_batch()` - Complex, unused

### KEEPING (Modern Architecture)

**Silver Layer**:
- ✅ `get_silver_dataframe()` - Loads raw data from BigQuery FDW (with retry logic)
- ✅ `_get_column_mapping()` - Maps source columns to canonical names

**Star Schema Write (Analytics V2)**:
- ✅ `write_star_customers()` - Bulk insert to dim_customer
- ✅ `write_star_suppliers()` - Bulk insert to dim_supplier
- ✅ `write_star_products()` - Bulk insert to dim_product
- ✅ `write_fact_sales()` - Bulk insert transactional data (with optimized FK lookups)
- ✅ `write_star_time_series()` - No-op (view computes)
- ✅ `write_star_regional()` - No-op (view computes)
- ✅ `write_star_last_orders()` - No-op (view computes)
- ✅ `write_star_customer_products()` - No-op (view computes)

**Star Schema Read (Analytics V2)**:
- ✅ `get_v2_time_series()` - Read from v_time_series view
- ✅ `get_v2_regional()` - Read from v_regional view
- ✅ `get_v2_last_orders()` - Read from v_last_orders view
- ✅ `get_v2_customer_products()` - Read from v_customer_products view

**Client Management**:
- ✅ `get_or_create_cliente_vizu_id()` - Create/get cliente_vizu
- ✅ `ensure_cliente_vizu_exists()` - Ensure user exists, return client_id

**Utility**:
- ✅ `_sanitize_numeric()` - Prevent NaN/Inf in calculations

## Expected Result

- **Before**: 2,415 lines (70% deprecated code)
- **After**: ~600-700 lines (clean, focused, modern)
- **Reduction**: ~72% less code
- **Benefit**: Easier maintenance, clearer intent, faster development

## File Locations

**File**: `services/analytics_api/src/analytics_api/data_access/postgres_repository.py`

**Lines to remove** (approximate counts):
- Gold write methods: ~750 lines
- Gold read methods: ~900 lines
- Old metric helpers: ~400 lines
- **Total removal**: ~2,050 lines
- **Keep**: ~365 lines (core modern code)
