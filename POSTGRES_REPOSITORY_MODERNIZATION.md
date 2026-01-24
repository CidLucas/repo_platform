# PostgreSQL Repository Modernization - Next Steps

## Status: Review Complete

The `postgres_repository.py` file is 2,415 lines with significant technical debt from transitioning from Gold schema (old) to Star schema V2 (new).

## Key Findings

### What's Working
- ✅ `get_silver_dataframe()` - with SSL retry logic (excellent)
- ✅ `write_star_*()` methods - modern bulk inserts (lines 1391-1677)
- ✅ `get_v2_*()` methods - reading from views (lines 2278-2377)
- ✅ `ensure_cliente_vizu_exists()` - client management

### Code Bloat Issues

**Total Methods**: 54 public methods
**Useful Methods**: 8-10
**Deprecated Methods**: ~40+
**Estimated Waste**: ~2,050 lines (85% of file)

### Deprecated Patterns to Remove

**Gold Schema Writes** (lines 678-1379):
- `write_gold_customers()` through `write_gold_last_orders()` → 700+ lines
- All replaced by `write_star_*()` and materialized views

**Gold Schema Reads** (lines 484-1050):
- `get_gold_*()` methods → 600+ lines
- Replaced by `get_v2_*()` methods which query views

**Old Helper Methods** (lines 210-476):
- `get_order_metrics_by_date_range()`, `_get_gold_table_*()`, etc.
- Only used by deprecated methods → 350+ lines

**Complex Metrics** (lines 1847-2072):
- `get_comparison_metrics_from_time_series()`
- `get_all_comparison_metrics_batch()`
- `calculate_growth_from_time_series()`
- Complex but unused in current API → 250+ lines

### Why This Matters

1. **Maintenance Cost**: Every bug fix requires updates in 2+ places
2. **Testing**: Multiple paths to same functionality
3. **Documentation**: Confusing which methods to use
4. **Performance**: Some methods make multiple queries
5. **Onboarding**: New devs don't know gold vs v2 vs silver

## Recommended Approach

### Option A: Surgical Removal (Recommended)
Remove methods in this order to minimize integration issues:

**Phase 1** (Low Risk - No Code Uses These):
- Remove helper methods: `_get_gold_table_*()`, `_get_period_date_range()`
- Remove unused metrics: `calculate_growth_from_time_series()`, comparison methods
- Remove legacy distinct methods: `get_distinct_products()`, `get_distinct_customers()`
- **Impact**: ~650 lines removed, 0 code changes needed

**Phase 2** (Medium Risk - Some Code Uses Gold Fallback):
- Remove write_gold_* methods (only write_star_* should write)
- Remove non-fallback get_gold_* methods
- Keep fallback methods: `get_gold_*` (used when views are empty)
- **Impact**: ~1,000 lines removed, update ETL to not call write_gold_*

**Phase 3** (Safe - Keep Forever):
- Keep all `get_v2_*()` methods (primary reads)
- Keep all `write_star_*()` methods (primary writes)
- Keep gold fallbacks (safety net while views populate)
- Keep `get_silver_dataframe()` (source of truth)
- Keep `ensure_cliente_vizu_exists()` (user management)
- **Impact**: ~400 lines of useful code

### Timeline

**Now**: Remove Phase 1 (high confidence, zero risk)
- `_get_gold_table_single()`, `_get_gold_table_multiple()`, `_get_period_date_range()`
- `calculate_growth_from_time_series()`, `get_comparison_metrics_from_time_series()`, `get_all_comparison_metrics_batch()`
- `get_distinct_products()`, `get_distinct_customers()`
- `get_order_metrics_by_date_range()`, `get_product_metrics_by_date_range()`, `get_customer_metrics_by_date_range()`
- **Lines removed**: ~650
- **Result**: 1,765 lines (27% reduction)

**After Testing**: Remove Phase 2 (medium confidence)
- Remove all `write_gold_*()` (lines 678-1379)
- Keep fallback `get_gold_*()` for safety
- **Lines removed**: ~700
- **Result**: 1,065 lines (56% reduction)

**After Stability**: Phase 3 (keep good code)
- Final result: ~400 lines core modern code + safety fallbacks = ~700 lines total

## What to Keep (Permanent)

```python
# CORE ARCHITECTURE
- get_silver_dataframe()                  # Load raw data from BigQuery FDW
- _get_column_mapping()                   # Map source columns to canonical
- _sanitize_numeric()                     # Data validation

# STAR SCHEMA WRITES (Primary path)
- write_star_customers()                  # Bulk insert dim_customer
- write_star_suppliers()                  # Bulk insert dim_supplier
- write_star_products()                   # Bulk insert dim_product
- write_fact_sales()                      # Bulk insert transactions
- write_star_time_series()                # No-op (view computes)
- write_star_regional()                   # No-op (view computes)
- write_star_last_orders()                # No-op (view computes)
- write_star_customer_products()          # No-op (view computes)

# STAR SCHEMA READS (Primary path)
- get_v2_time_series()                    # Read from v_time_series
- get_v2_regional()                       # Read from v_regional
- get_v2_last_orders()                    # Read from v_last_orders
- get_v2_customer_products()              # Read from v_customer_products

# GOLD READS (Fallbacks - keep for now)
- get_gold_time_series()                  # Fallback if views empty
- get_gold_regional()                     # Fallback if views empty
- get_gold_last_orders()                  # Fallback if views empty
- get_gold_customer_products()            # Fallback if views empty
- get_gold_time_series_with_dates()       # Utility
- get_gold_products_aggregated()          # Utility
- get_gold_customers_aggregated()         # Utility

# USER MANAGEMENT (Keep)
- get_or_create_cliente_vizu_id()         # Legacy client creation
- ensure_cliente_vizu_exists()            # Modern client management

# REMOVE COMPLETELY
- All write_gold_*() methods              # Replaced by write_star_*()
- write_fact_order_metrics()              # Table doesn't exist
- write_fact_product_metrics()            # Table doesn't exist
- All get_order_metrics_by_date_range()   # Old pattern
- All get_product_metrics_by_date_range() # Old pattern
- All get_customer_metrics_by_date_range()# Old pattern
- get_products_by_customer_cpf_cnpj()     # Redundant with v2
- get_distinct_products()                 # Unused
- get_distinct_customers()                # Unused
- _get_gold_table_single()                # Helper only for gold
- _get_gold_table_multiple()              # Helper only for gold
- _get_period_date_range()                # Helper only for gold
- calculate_growth_from_time_series()     # Unused complex metric
- get_comparison_metrics_from_time_series()# Unused complex metric
- get_all_comparison_metrics_batch()      # Unused complex metric
```

## Next Action

Ready to proceed with Phase 1 removal (650 lines, zero risk)?

**Files to edit**:
- `/services/analytics_api/src/analytics_api/data_access/postgres_repository.py`

**Expected result**:
- 1,765 lines (72% waste removed)
- Zero API changes needed
- No code in ETL needs updating
- Cleaner, more maintainable codebase
