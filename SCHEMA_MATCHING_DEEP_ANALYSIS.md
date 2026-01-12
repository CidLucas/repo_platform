# Schema Matching Deep Analysis & Troubleshooting

## Executive Summary

After analyzing the logs, I found **3 critical issues** and **several opportunities for improvement**:

1. ❌ **Missing `order_id` column** → Causes KeyError in aggregations
2. ⚠️ **Poor conflict resolution** → Only 9/84 columns mapped (89% lost!)
3. ⚠️ **No data quality monitoring** → Can't assess mapping effectiveness

---

## Issue 1: Missing `order_id` Column (CRITICAL) 🔴

### Problem

```
Missing canonical columns: ['order_id']
ERROR: 'num_pedidos_unicos'
KeyError at line 144: agg_df['ticket_medio'] = agg_df['receita_total'] / agg_df['num_pedidos_unicos']
```

### Root Cause

The aggregation logic at [metric_service.py:127](services/analytics_api/src/analytics_api/services/metric_service.py#L127) requires `order_id`:

```python
if 'order_id' in df.columns:
    agg_ops['num_pedidos_unicos'] = ('order_id', 'nunique')
```

But `order_id` was never matched from BigQuery columns. Looking at the conflict logs:

```
Conflict: 11 columns map to 'data_transacao'
  - createdat_product (1.00) ✓ CHOSEN
  - createdat_operatorinvoice (1.00) ✗ REJECTED
```

**Hypothesis**: `id_operatorinvoice` exists in BigQuery but either:
1. Lost in conflict resolution
2. Doesn't match any alias for `order_id`
3. Doesn't exist in the source table

### Solution A: Add Alias for Order ID

Check `COLUMN_ALIASES` in schema_matcher_service.py for `order_id`:

```python
COLUMN_ALIASES = {
    ...
    "order_id": [
        "id_operatorinvoice",  # ← ADD THIS
        "invoice_id",
        "pedido_id",
        "order_number"
    ],
    ...
}
```

### Solution B: Generate Synthetic Order ID

If no natural order_id exists, generate one in the Analytics API:

```python
# In postgres_repository.py after loading dataframe
if 'order_id' not in df.columns:
    logger.warning("⚠️  order_id missing, generating synthetic IDs")
    # Option 1: Use row index
    df['order_id'] = df.index.astype(str)

    # Option 2: Hash transaction details (better for grouping)
    df['order_id'] = (
        df['emitter_nome'].astype(str) + '_' +
        df['data_transacao'].astype(str) + '_' +
        df['valor_total_emitter'].astype(str)
    ).apply(lambda x: hash(x) % 10**8)  # 8-digit hash
```

### Solution C: Make Aggregations Resilient

Modify [metric_service.py:144-145](services/analytics_api/src/analytics_api/services/metric_service.py#L144-L145) to handle missing `num_pedidos_unicos`:

```python
# Instead of:
agg_df['ticket_medio'] = agg_df['receita_total'] / agg_df['num_pedidos_unicos']

# Use:
if 'num_pedidos_unicos' in agg_df.columns:
    agg_df['ticket_medio'] = agg_df['receita_total'] / agg_df['num_pedidos_unicos']
else:
    logger.warning("⚠️  num_pedidos_unicos not available, using receita_total as ticket_medio")
    agg_df['ticket_medio'] = agg_df['receita_total']  # Fallback
    agg_df['num_pedidos_unicos'] = 1  # Assume 1 order per entity
```

**Recommended**: Implement **all three** for defense in depth.

---

## Issue 2: Poor Conflict Resolution (MAJOR) ⚠️

### Problem

```
✓ Mapped: 9 columns
✗ UNMATCHED: 75 columns (89% DATA LOSS!)

Conflicts:
  - 5 columns → raw_product_description (kept 1, lost 4)
  - 11 columns → data_transacao (kept 1, lost 10)
  - 6 columns → receiver_nome (kept 1, lost 5)
```

### Root Cause

Current conflict resolution in [schema_matcher_service.py:666-690](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L666-L690):

```python
candidates.sort(key=lambda _c: _c[1], reverse=True)  # Sort by score
best_candidate, best_score = candidates[0]  # Pick first
```

**Problem**: When multiple columns have **exact match (1.0 score)**, it picks arbitrarily (first in list). This is why we lose valuable columns:

```
'material' (1.00) → raw_product_description ✗ REJECTED
'ncm' (1.00) → raw_product_description ✗ REJECTED
```

Both `material` and `ncm` are valid product fields, but only `description_product` was kept!

### Solution: Multi-Criteria Tiebreaker

When multiple candidates have the same score, use **secondary criteria**:

```python
# In auto_match() after first pass
for canonical, candidates in canonical_matches.items():
    if len(candidates) > 1:
        # Sort by: 1) Score DESC, 2) Name length ASC, 3) Fuzzy similarity DESC
        candidates.sort(key=lambda c: (
            -c[1],  # Higher score first
            len(c[0]),  # Shorter name first (more specific)
            -self.calculate_similarity(c[0], canonical)  # Higher fuzzy sim first
        ))

        best_candidate, best_score = candidates[0]

        # SPECIAL HANDLING: If multiple exact matches (1.0), consider keeping BOTH
        exact_matches = [c for c in candidates if c[1] == 1.0]
        if len(exact_matches) > 1:
            logger.warning(
                f"  ⚠ Multiple exact matches for '{canonical}': {[c[0] for c in exact_matches]}"
            )
            # Option 1: Keep all with suffixes
            # result.matched[f"{exact_matches[0][0]}"] = canonical
            # result.matched[f"{exact_matches[1][0]}_alt"] = f"{canonical}_alt"

            # Option 2: Pick shortest name (likely more specific)
            exact_matches.sort(key=lambda c: len(c[0]))
            best_candidate = exact_matches[0][0]
```

### Solution B: Expand Canonical Schema

Instead of forcing multiple columns into one canonical, **expand the schema**:

```python
CANONICAL_SCHEMAS = {
    "invoices": [
        # ... existing columns ...
        "raw_product_description",
        "product_material",      # NEW: Map 'material' here
        "product_ncm",           # NEW: Map 'ncm' here
        "quantidade",
        "quantidade_kg",         # NEW: Map 'quantitytradedkg_product' here
        "createdat_product",     # NEW: Specific timestamp
        "createdat_invoice",     # NEW: Different timestamp
        # ... etc
    ],
}
```

This way, we don't lose data in conflicts!

---

## Issue 3: Quantity Unit Conflict ⚠️

### Problem

```
⚠ Conflict: 'quantitytraded_product' (1.00) over ['quantitytradedkg_product'(1.00)]
```

Both map to `quantidade`, but one is in **units** and one is in **kilograms**!

### Solution

**Option A**: Keep both with unit suffix

```python
"quantidade": ["quantitytraded_product", "quantity", "qty"],
"quantidade_kg": ["quantitytradedkg_product", "quantity_kg"],
```

**Option B**: Store unit metadata

```python
# In column_mapping, store tuples: (source_col, unit)
{
    "quantitytraded_product": ("quantidade", "units"),
    "quantitytradedkg_product": ("quantidade", "kg"),
}
```

**Option C**: Convert to standard unit

```python
# In Analytics API after loading
if 'quantidade_kg' in df.columns and 'quantidade' not in df.columns:
    # Assume 1 unit = 1 kg average (or use product-specific conversion)
    df['quantidade'] = df['quantidade_kg'] / df.get('peso_medio_kg', 1.0)
```

---

## Issue 4: No Data Quality Monitoring ⚠️

### Current State

We know:
- ✅ 9 columns mapped
- ❌ 75 columns unmapped
- ❓ How many canonical columns are filled?
- ❓ What % of rows have NULL values?
- ❓ Which canonical columns have 0% coverage?

### Solution: Add Quality Metrics

#### A. In ETL Service (after matching)

```python
# In etl_service_v2.py after schema matching
logger.info(f"\n{'='*80}")
logger.info(f"[MAPPING QUALITY ASSESSMENT]")

# 1. Coverage: What % of canonical schema was filled?
canonical_cols = schema_matcher.get_canonical_schema(schema_type_for_match)
mapped_canonical = set(mapping_dict.values())
coverage_pct = (len(mapped_canonical) / len(canonical_cols)) * 100

logger.info(f"  Schema Coverage: {len(mapped_canonical)}/{len(canonical_cols)} ({coverage_pct:.1f}%)")
logger.info(f"  Mapped canonical columns: {sorted(mapped_canonical)}")

unmapped_canonical = set(canonical_cols) - mapped_canonical
if unmapped_canonical:
    logger.warning(f"  ⚠️  Unmapped canonical columns: {sorted(unmapped_canonical)}")

# 2. Data loss: What % of source columns were used?
usage_pct = (len(mapping_dict) / len(source_column_names)) * 100
logger.warning(f"  Source Column Usage: {len(mapping_dict)}/{len(source_column_names)} ({usage_pct:.1f}%)")
logger.warning(f"  ⚠️  Data Loss: {len(match_result.unmatched)} columns unmapped ({100-usage_pct:.1f}%)")

logger.info(f"{'='*80}\n")
```

#### B. In Analytics API (after loading data)

```python
# In postgres_repository.py after loading DataFrame
logger.info(f"\n{'='*80}")
logger.info(f"[DATA QUALITY CHECK]")

for col in df.columns:
    null_pct = (df[col].isna().sum() / len(df)) * 100
    unique_vals = df[col].nunique()

    if null_pct > 50:
        logger.warning(f"  ⚠️  {col}: {null_pct:.1f}% NULL (low quality)")
    elif null_pct > 0:
        logger.info(f"  ℹ️  {col}: {null_pct:.1f}% NULL, {unique_vals} unique values")
    else:
        logger.info(f"  ✓ {col}: 100% populated, {unique_vals} unique values")

logger.info(f"{'='*80}\n")
```

#### C. Store Metrics in Database

Create a new table to track mapping quality over time:

```sql
CREATE TABLE schema_mapping_quality (
    id SERIAL PRIMARY KEY,
    client_id UUID NOT NULL,
    resource_type TEXT NOT NULL,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Coverage metrics
    total_source_columns INT,
    mapped_source_columns INT,
    unmapped_source_columns INT,
    source_usage_pct DECIMAL(5,2),

    total_canonical_columns INT,
    filled_canonical_columns INT,
    missing_canonical_columns INT,
    canonical_coverage_pct DECIMAL(5,2),

    -- Quality metrics
    high_confidence_matches INT,
    medium_confidence_matches INT,
    low_confidence_matches INT,
    conflict_count INT,

    -- Data quality (per canonical column)
    null_percentage JSONB,  -- {"emitter_nome": 0.5, "receiver_nome": 10.2}
    unique_value_counts JSONB  -- {"emitter_nome": 1234, "receiver_nome": 5678}
);
```

---

## Recommended Action Plan

### Immediate Fixes (P0 - Required for system to work)

1. **Fix KeyError** (metric_service.py)
   - Add defensive checks for `num_pedidos_unicos`
   - Generate synthetic `order_id` if missing

2. **Add `order_id` Alias** (schema_matcher_service.py)
   - Add `"id_operatorinvoice"` to `order_id` aliases
   - Re-run sync to test

### Short-term Improvements (P1 - Improve mapping quality)

3. **Improve Conflict Resolution**
   - Implement multi-criteria tiebreaker (score → length → fuzzy)
   - Add special handling for exact match conflicts

4. **Expand Canonical Schema**
   - Add `product_material`, `product_ncm` columns
   - Add `quantidade_kg` alongside `quantidade`
   - Add multiple timestamp columns for different contexts

### Long-term Enhancements (P2 - Monitoring & observability)

5. **Add Quality Metrics**
   - Log mapping coverage and data loss percentages
   - Track NULL percentages per column
   - Store historical metrics in database

6. **Build Admin UI**
   - Show mapping quality dashboard
   - Allow manual column mapping adjustments
   - Highlight low-quality or ambiguous mappings

---

## Immediate Next Steps

1. **Run this query** to see what columns exist in BigQuery:

```sql
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'products_invoices'
ORDER BY column_name;
```

Look for: `id_operatorinvoice`, `order_id`, `invoice_id`, etc.

2. **Check alias cache** in logs - does it contain `order_id` mappings?

```python
# Add this logging in _build_alias_cache()
logger.info(f"Aliases for 'order_id': {self.COLUMN_ALIASES.get('order_id', [])}")
logger.info(f"Cache entries for 'order_id': {[k for k, v in self._alias_to_canonical['invoices'].items() if v == 'order_id']}")
```

3. **Apply defensive fix** to metric_service.py **immediately** to unblock the system.

4. **Re-run sync** and collect full logs to analyze which columns were considered for `order_id`.

---

## Summary

| Issue | Severity | Impact | Fix Complexity |
|-------|----------|--------|----------------|
| Missing `order_id` | 🔴 Critical | System broken | Low (add alias) |
| Poor conflict resolution | ⚠️ Major | 89% data loss | Medium |
| Quantity unit conflicts | ⚠️ Minor | Data accuracy | Low (expand schema) |
| No quality monitoring | ℹ️ Info | Debugging hard | Medium |

**Bottom Line**: The schema matcher is working, but conflict resolution needs to be smarter. We're losing 75/84 columns (89%!) due to conflicts, and the missing `order_id` breaks aggregations entirely.
