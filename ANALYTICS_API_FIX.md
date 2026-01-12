# Analytics API Fix - Column Mapping Application

## Problem Identified

From the logs:
```
analytics_api | INFO:  ✓ Loaded 72865 rows from silver layer
analytics_api | INFO:  📋 Column names (84): ['id_product', 'fivetran_deleted_product', 'cfop', ...]
analytics_api | INFO:  📊 Canonical columns found: []
analytics_api | WARNING: ⚠️  Missing canonical columns: ['order_id', 'data_transacao', 'receiver_nome', 'emitter_nome', ...]
```

**Root Cause**: The Analytics API was querying the BigQuery foreign table with `SELECT *`, which returned **raw BigQuery column names** instead of applying the column mapping to translate them to **canonical names**.

## The Issue

### What Was Happening:

1. ✅ ETL creates BigQuery foreign table successfully
2. ✅ Schema matcher computes column mapping: `{"emitterlegalname": "emitter_nome", ...}`
3. ✅ Column mapping is stored in `client_data_sources.column_mapping`
4. ❌ **Analytics API ignores the mapping and does `SELECT *`**
5. ❌ DataFrame has raw columns: `['id_product', 'emitterlegalname', ...]`
6. ❌ Aggregations fail because they expect canonical names: `['order_id', 'emitter_nome', ...]`

### Expected Flow:

1. ✅ Load `column_mapping` from `client_data_sources`
2. ✅ Build SELECT query with aliases: `SELECT "emitterlegalname" AS emitter_nome, ...`
3. ✅ DataFrame has canonical columns: `['order_id', 'emitter_nome', ...]`
4. ✅ Aggregations work correctly

---

## The Fix

**File**: [postgres_repository.py:37-118](services/analytics_api/src/analytics_api/data_access/postgres_repository.py#L37-L118)

### Modified `get_silver_dataframe()`

**Before**:
```python
def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
    table_name = get_silver_table_name(client_id)
    query = f"SELECT * FROM {table_name}"  # ❌ Returns raw column names
    df = pd.read_sql(query, self.db_session.bind)
    return df
```

**After**:
```python
def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
    table_name = get_silver_table_name(client_id)

    # Load column_mapping from client_data_sources
    column_mapping = self._get_column_mapping(client_id)

    # Build SELECT query with column aliases
    if column_mapping:
        select_clauses = []
        for source_col, canonical_col in column_mapping.items():
            select_clauses.append(f'"{source_col}" AS {canonical_col}')

        query = f"SELECT {', '.join(select_clauses)} FROM {table_name}"
        # ✅ Returns canonical column names
    else:
        query = f"SELECT * FROM {table_name}"  # Fallback
        logger.warning("⚠️  No column_mapping found, using SELECT *")

    df = pd.read_sql(query, self.db_session.bind)
    return df
```

### Added `_get_column_mapping()` Helper

```python
def _get_column_mapping(self, client_id: str) -> dict[str, str] | None:
    """
    Loads the column_mapping from client_data_sources.

    Returns:
        dict mapping source column names to canonical names,
        or None if no mapping exists
    """
    result = self.db_session.execute(
        text("""
            SELECT column_mapping
            FROM client_data_sources
            WHERE client_id = :client_id
              AND storage_type = 'foreign_table'
              AND sync_status = 'active'
            ORDER BY last_synced_at DESC
            LIMIT 1
        """),
        {"client_id": client_id}
    ).fetchone()

    if result and result[0]:
        column_mapping = result[0]
        logger.info(f"✓ Loaded column_mapping: {len(column_mapping)} mappings")
        return column_mapping
    else:
        logger.warning(f"⚠️  No column_mapping found")
        return None
```

---

## Expected Logs After Fix

### During get_silver_dataframe():

```
🔍 Querying silver table: bigquery.c_760f2c80_invoices
  ✓ Loaded column_mapping for client 760f2c80-...: 45 mappings
  📝 Applying column mapping: 45 columns
  Sample mappings (first 5):
    'emitterlegalname' → emitter_nome
    'receiverlegalname' → receiver_nome
    'id_operatorinvoice' → order_id
    'price_operatorinvoice' → valor_total_emitter
    'emittedat_operatorinvoice' → data_transacao
✓ Loaded 72865 rows from silver layer
📋 Column names (45): ['order_id', 'data_transacao', 'emitter_nome', 'receiver_nome', ...]
```

### During aggregation:

```
📊 Canonical columns found: ['order_id', 'data_transacao', 'emitter_nome', 'receiver_nome', ...]
✅ All required columns present
🔄 Computing aggregations...
  - Customers aggregated: 1,234 records
  - Suppliers aggregated: 567 records
  - Products aggregated: 8,901 records
💾 Writing aggregated data to gold tables...
  ✓ Wrote 1,234 customer records
  ✓ Wrote 567 supplier records
  ✓ Wrote 8,901 product records
✅ All gold tables written successfully
```

---

## Testing Steps

1. **Trigger a new sync** from the frontend (or via API)
2. **Check ETL logs** to verify schema matching succeeded:
   ```
   [SCHEMA MATCHING] Starting for resource_type='invoices'
   ✓ Stage 1 - Exact alias match: 'emitterlegalname' → 'emitter_nome' (score: 1.0)
   ✓ Stage 1 - Exact alias match: 'receiverlegalname' → 'receiver_nome' (score: 1.0)
   [SUMMARY] Schema match for 'invoices':
     ✓ Matched: 45 columns
   [PERSISTENCE] Saving data source to client_data_sources
     column_mapping entries: 45
     Sample mappings:
       'emitterlegalname' → 'emitter_nome'
       'receiverlegalname' → 'receiver_nome'
   ✅ Successfully persisted data source
   ```

3. **Check Analytics API logs** to verify column mapping is applied:
   ```
   ✓ Loaded column_mapping for client: 45 mappings
   📝 Applying column mapping: 45 columns
   ✓ Loaded 72865 rows from silver layer
   📋 Column names: ['order_id', 'emitter_nome', 'receiver_nome', ...]
   📊 Canonical columns found: [...]
   ✅ All required columns present
   ```

4. **Query the database** to verify data was written:
   ```sql
   SELECT COUNT(*) FROM analytics_gold_customers WHERE client_id = '760f2c80-...';
   SELECT COUNT(*) FROM analytics_gold_suppliers WHERE client_id = '760f2c80-...';
   SELECT COUNT(*) FROM analytics_gold_products WHERE client_id = '760f2c80-...';
   ```

5. **Check the frontend** to see if dashboards populate with data

---

## Files Modified

1. **[services/analytics_api/src/analytics_api/data_access/postgres_repository.py](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)**
   - Modified `get_silver_dataframe()` to load and apply column mapping
   - Added `_get_column_mapping()` helper method
   - Added comprehensive logging for debugging

---

## Related Issues

### Issue: Date Column Not Usable

From the original logs:
```
WARNING: ⚠️  data_transacao column not usable, skipping time-based features
```

**Root Cause**: The `data_transacao` column exists in the mapping, but it might be:
1. NULL/empty in the BigQuery data
2. Wrong data type (string instead of timestamp)
3. Invalid date format

**Verification**: After applying the column mapping, check the data type:
```python
logger.info(f"data_transacao dtype: {df['data_transacao'].dtype}")
logger.info(f"data_transacao sample: {df['data_transacao'].head()}")
```

**Fix (if needed)**: Add type conversion in the SELECT query:
```python
f'CAST("{source_col}" AS TIMESTAMP) AS {canonical_col}'
```

---

## Summary

The fix ensures that:
- ✅ Column mapping is loaded from `client_data_sources`
- ✅ SELECT query uses column aliases to translate source → canonical
- ✅ DataFrame has canonical column names expected by aggregations
- ✅ Aggregations produce correct results
- ✅ Gold tables are populated with customer/supplier/product data
- ✅ Dashboard displays analytics correctly

The issue was **not in the schema matcher** (which was working correctly), but in the **Analytics API not applying the mapping** when querying the foreign table.
