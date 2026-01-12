# Conflict Resolution Tiebreaker Fix

## Problem

When multiple source columns had equal match scores (1.0) for the same canonical column, the conflict resolution was using **name length** as a tiebreaker, which didn't make sense.

**Example**:
```
'material' (score: 1.00, length: 8) → raw_product_description ✗ REJECTED
'description_product' (score: 1.00, length: 19) → raw_product_description ✓ CHOSEN
```

The system was picking the column with the **shorter name**, assuming it was more specific. However, this was arbitrary and could reject better matches.

---

## User Feedback

> "This does not make sense, remove the length comparison, use only the fuzzy score. We compare the fuzzy score only when there are more than one candidate, candidates by similarity or by exact match."

---

## The Fix

**File**: [schema_matcher_service.py:680-699](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L680-L699)

### Before:
```python
candidates_sorted = sorted(candidates, key=lambda c: (
    -c[1],  # Higher score first
    len(c[0]),  # Shorter name first ← REMOVED
    -self.calculate_similarity(c[0].lower(), canonical.lower())  # Higher similarity
))
```

### After:
```python
candidates_sorted = sorted(candidates, key=lambda c: (
    -c[1],  # Higher score first (from find_best_match)
    -self.calculate_similarity(c[0].lower(), canonical.lower())  # Higher fuzzy similarity as tiebreaker
))
```

---

## How It Works Now

### Multi-Criteria Conflict Resolution:

1. **Primary Sort**: Match score (descending)
   - Score from `find_best_match()` (exact alias, normalized match, type match, fuzzy match)
   - Higher score = better match

2. **Tiebreaker** (only when scores are equal): Fuzzy similarity (descending)
   - Uses `difflib.SequenceMatcher` to compute similarity between source and canonical column names
   - Higher similarity = closer string match

### Example:

Given canonical column: `raw_product_description`

**Candidates**:
- `description_product` (score: 1.0, fuzzy: 0.82)
- `material` (score: 1.0, fuzzy: 0.35)
- `ncm` (score: 1.0, fuzzy: 0.20)

**Resolution**:
1. All have equal score (1.0) → need tiebreaker
2. Compare fuzzy similarity:
   - `description_product` vs `raw_product_description` → 0.82 (high similarity)
   - `material` vs `raw_product_description` → 0.35
   - `ncm` vs `raw_product_description` → 0.20
3. **Winner**: `description_product` (highest fuzzy similarity)

---

## Expected Logs After Fix

```
[CONFLICT RESOLUTION] Resolving 12 potential matches

  ⚠ Conflict: 5 columns with equal score (1.00) map to 'raw_product_description'.
  Using tiebreaker (fuzzy similarity): 'description_product' chosen over ['material', 'ncm', 'produto_descricao', 'item_desc']

  ⚠ Conflict: 11 columns with equal score (1.00) map to 'data_transacao'.
  Using tiebreaker (fuzzy similarity): 'emittedat_operatorinvoice' chosen over ['createdat_product', 'createdat_invoicecredit', ...]

[SUMMARY] Schema match for 'invoices':
  ✓ Matched: 10 columns
  ✗ UNMATCHED: 74 columns
```

---

## Impact

### Before (with length comparison):
- Arbitrary selection based on name length
- Could reject better semantic matches
- Less predictable results

### After (fuzzy similarity only):
- Selects the column name most similar to the canonical name
- More semantically meaningful choices
- More predictable and explainable results

---

## Testing

### 1. Run a new sync with BigQuery data:
```bash
curl -X POST http://localhost:8002/api/etl/bigquery/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "project_id": "your-project",
    "dataset_id": "your-dataset",
    "table_id": "invoices",
    "resource_type": "invoices"
  }'
```

### 2. Check logs for conflict resolution:
```bash
docker-compose logs data_ingestion_api | grep "Using tiebreaker"
```

### 3. Verify the chosen columns make sense:
- Look at the winner in each conflict
- Compare fuzzy similarity scores
- Ensure the most similar column name was chosen

---

## Files Modified

1. **services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py** (lines 680-699)
   - Removed `len(c[0])` from sort key
   - Updated comment to reflect only score + fuzzy similarity
   - Updated log message to say "fuzzy similarity" instead of "name length + fuzzy similarity"

---

## Related Documentation

- [FIXES_IMPLEMENTED_SUMMARY.md](FIXES_IMPLEMENTED_SUMMARY.md) - Complete schema matching fixes
- [SCHEMA_MATCHING_DEEP_ANALYSIS.md](SCHEMA_MATCHING_DEEP_ANALYSIS.md) - Deep analysis of the matching algorithm
- [ANALYTICS_API_FIX.md](ANALYTICS_API_FIX.md) - How Analytics API applies column mappings

---

## Summary

✅ **Removed**: Name length comparison (arbitrary and meaningless)
✅ **Kept**: Primary score + fuzzy similarity tiebreaker
✅ **Result**: More semantically meaningful column selection in conflicts
✅ **User Feedback**: Aligned with user's request to use only fuzzy score for tiebreaking

The conflict resolution now makes intelligent choices based on string similarity when multiple columns have equal match scores.
