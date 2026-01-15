# Time Series Batch Write Fix

## Problem Discovered

After adding `produtos_no_tempo` and `pedidos_no_tempo`, only **pedidos_no_tempo** was showing in the database, with all other time series missing.

### Root Cause

The `write_gold_time_series()` method in `postgres_repository.py` **deletes ALL time series data** for the client before inserting:

```python
# Line 716-719
self.db_session.execute(
    text("DELETE FROM analytics_gold_time_series WHERE client_id = :client_id"),
    {"client_id": client_id}
)
```

Since each time series was being written **separately**:
1. Write fornecedores_no_tempo → **Deletes everything**, writes fornecedores (4 points)
2. Write clientes_no_tempo → **Deletes fornecedores**, writes clientes (4 points)
3. Write produtos_no_tempo → **Deletes clientes**, writes produtos (4 points)
4. Write pedidos_no_tempo → **Deletes produtos**, writes pedidos (4 points)

**Result:** Only the last time series (pedidos_no_tempo) remained in the database!

---

## Solution Applied

Changed `_write_time_series_charts()` to **collect all time series data first**, then write in a **single batch**.

### Before (Incorrect - 4 separate writes)

```python
# Fornecedores
if chart_data:
    self.repository.write_gold_time_series(self.client_id, chart_data)  # DELETE ALL, write 4

# Clientes
if chart_data:
    self.repository.write_gold_time_series(self.client_id, chart_data)  # DELETE ALL, write 4

# Produtos
if chart_data:
    self.repository.write_gold_time_series(self.client_id, chart_data)  # DELETE ALL, write 4

# Pedidos
if chart_data:
    self.repository.write_gold_time_series(self.client_id, chart_data)  # DELETE ALL, write 4
```

### After (Correct - 1 batch write)

**File:** [metric_service.py:477-601](services/analytics_api/src/analytics_api/services/metric_service.py)

```python
def _write_time_series_charts(self) -> None:
    """Compute and write time-series aggregations (fornecedores_no_tempo, etc.)"""
    try:
        # Collect ALL time series data first, then write in a single batch
        all_time_series_data = []

        # Fornecedores no tempo
        if 'emitter_nome' in self.df.columns:
            # ... compute chart_data ...
            all_time_series_data.extend(chart_data)
            logger.info(f"  ✓ Computed {len(chart_data)} fornecedores time series points")

        # Clientes no tempo
        if 'receiver_nome' in self.df.columns:
            # ... compute chart_data ...
            all_time_series_data.extend(chart_data)
            logger.info(f"  ✓ Computed {len(chart_data)} clientes time series points")

        # Produtos no tempo
        if 'raw_product_description' in self.df.columns:
            # ... compute chart_data ...
            all_time_series_data.extend(chart_data)
            logger.info(f"  ✓ Computed {len(chart_data)} produtos time series points")

        # Pedidos no tempo
        if 'order_id' in self.df.columns:
            # ... compute chart_data ...
            all_time_series_data.extend(chart_data)
            logger.info(f"  ✓ Computed {len(chart_data)} pedidos time series points")

        # Write all time series data in a single batch
        if all_time_series_data:
            self.repository.write_gold_time_series(self.client_id, all_time_series_data)
            logger.info(f"  ✓ Written total of {len(all_time_series_data)} time series points to database")
```

---

## Key Changes

1. **Added `all_time_series_data = []`** at the beginning to collect all data
2. **Changed from `write_gold_time_series()` to `extend()`** for each time series type
3. **Single `write_gold_time_series()` call** at the end with all collected data
4. **Updated logging** to show "Computed" vs "Written"

---

## Test Results

### Before Fix
```
✓ Written 4 fornecedores time series points
✓ Written 4 clientes time series points
✓ Written 4 produtos time series points
✓ Written 4 pedidos time series points

Database: Only pedidos_no_tempo present (last one wins)
```

### After Fix
```
✓ Computed 4 fornecedores time series points
✓ Computed 4 clientes time series points
✓ Computed 4 produtos time series points
✓ Computed 4 pedidos time series points
✓ Written total of 16 time series points to database

Database: ALL 4 time series present (4 points each = 16 total)
```

---

## Database Verification

After deploying this fix, verify all time series are present:

```sql
SELECT
    chart_type,
    COUNT(*) as point_count,
    MIN(period) as first_period,
    MAX(period) as last_period
FROM analytics_gold_time_series
WHERE client_id = 'your-client-id'
GROUP BY chart_type
ORDER BY chart_type;
```

**Expected Output:**
```
chart_type              | point_count | first_period | last_period
-----------------------|-------------|--------------|-------------
clientes_no_tempo      | 4           | 2025-10      | 2026-01
fornecedores_no_tempo  | 4           | 2025-10      | 2026-01
pedidos_no_tempo       | 4           | 2025-10      | 2026-01
produtos_no_tempo      | 4           | 2025-10      | 2026-01
```

---

## Alternative Solutions Considered

### Option 1: Delete only specific chart_type (Not Chosen)
Modify `write_gold_time_series()` to delete only the specific chart_type:
```python
# Delete only this chart type
self.db_session.execute(
    text("DELETE FROM analytics_gold_time_series WHERE client_id = :client_id AND chart_type = :chart_type"),
    {"client_id": client_id, "chart_type": chart_data[0].get("chart_type")}
)
```

**Why not chosen:**
- Would require 4 separate database transactions
- Less efficient than batch write
- Multiple DELETE operations instead of one

### Option 2: Batch write (Chosen)
Collect all time series data, then write once.

**Why chosen:**
- Single database transaction
- More efficient
- Cleaner code flow
- Matches pattern used for other chart types

---

## Impact on Regional Charts

Note: Regional charts (`_write_regional_charts()`) also call `write_gold_regional()` multiple times, but this works correctly because each call has a **different chart_type** and the repository method likely handles this differently.

If regional charts have the same issue, the same batch write pattern should be applied.

---

## Files Modified

1. **[metric_service.py:477-601](services/analytics_api/src/analytics_api/services/metric_service.py)**
   - Changed `_write_time_series_charts()` to use batch write pattern
   - Collect all time series data first
   - Single write call at the end

---

## Deployment Checklist

- [x] Fix batch write logic in `_write_time_series_charts()`
- [x] Test with sample data (all 4 time series present)
- [ ] **Deploy updated code to production**
- [ ] **Re-process existing client data**
- [ ] **Verify all 4 time series in database using SQL query above**
- [ ] **Monitor frontend charts to ensure all time series display correctly**
