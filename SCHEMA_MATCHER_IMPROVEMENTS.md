# Schema Matcher Improvements Summary

## Changes Made

### 1. **Simplified Normalization** ✅
**File**: [schema_matcher_service.py:442-454](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L442-L454)

**Before**:
- Lowercase
- Remove special characters
- Remove duplicate underscores
- Strip underscores
- Remove common prefixes (product_, order_, etc.)
- Remove leading numbers

**After**:
- **ONLY lowercase and strip whitespace**

**Rationale**: Excessive normalization was breaking exact matches. Column names like `"emitterlegalname"` should match the alias `"emitterlegalname"` exactly after lowercasing.

---

### 2. **Simplified Matching Stages** ✅
**File**: [schema_matcher_service.py:468-563](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L468-L563)

**Before**: 4 stages
1. Exact alias match
2. Exact normalized match (redundant)
3. Type-filtered fuzzy match
4. Global fuzzy match

**After**: 3 stages
1. **Exact match** (combines alias check + normalized comparison)
2. Type-filtered fuzzy match
3. Global fuzzy match

**Rationale**: Stage 1 and 2 were redundant since both checked exact matches after normalization. Combined into single stage.

**Added Logging**:
- `logger.info()` for each match attempt with normalized values
- `logger.debug()` for alias cache checks
- `logger.warning()` for failed matches
- Visual indicators (✓, ✗, ⚠) for easy scanning

---

### 3. **Improved Duplicate Handling** ✅
**File**: [schema_matcher_service.py:604-723](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L604-L723)

**Before**:
```python
if best_match in used_canonicals:
    # Try to find remaining columns, but might miss the BEST match
    remaining = [c for c in canonical_columns if c not in used_canonicals]
    best_match, score = find_best_match(source_col, remaining)
```

**After**:
```python
# Three-pass algorithm:
# Pass 1: Collect all potential matches
canonical_matches = {}  # canonical -> [(source, score), ...]
for source in sources:
    match, score = find_best_match(source, ...)
    canonical_matches[match].append((source, score))

# Pass 2: Resolve conflicts by picking HIGHEST SCORE
for canonical, candidates in canonical_matches.items():
    if len(candidates) > 1:
        candidates.sort(key=lambda c: c[1], reverse=True)
        best_candidate, best_score = candidates[0]
        # Use best_candidate, mark others as unmatched
```

**Rationale**:
- Old logic would arbitrarily pick the first match and prevent better matches later
- New logic evaluates ALL matches first, then picks the highest similarity score
- Rejected candidates are properly logged as warnings

**Example**:
```
Input columns: ["emitterlegalname", "emitterfantasyname"]
Both match "emitter_nome"

Old behavior: First one wins (non-deterministic)
New behavior: Pick the one with higher similarity score
              Log: "Conflict: 2 columns map to 'emitter_nome'.
                    Picking 'emitterlegalname' (1.0) over 'emitterfantasyname' (0.95)"
```

---

### 4. **Comprehensive Debug Logging** ✅

#### In `schema_matcher_service.py`:

**Match Start**:
```
[MATCH] Finding match for 'EmitterLegalName' (normalized: 'emitterlegalname')
  Checking alias cache for 'emitterlegalname' in schema 'invoices'
  Alias cache has 47 entries
```

**Match Success**:
```
  ✓ Stage 1 - Exact alias match: 'emitterlegalname' → 'emitter_nome' (score: 1.0)
```

**Match Failure**:
```
  ✗ No exact match found for 'unknown_column'
  Inferred type for 'unknown_column': string
  Found 15 type-compatible columns (out of 45)
  ✗ Best type-compatible match score 0.52 below 0.6 threshold
  ✗ No good match found for 'unknown_column' (best: 'some_column' with score 0.45)
```

**Conflict Resolution**:
```
[CONFLICT RESOLUTION] Resolving 12 potential matches
  ⚠ Conflict: 2 columns map to 'emitter_nome'.
     Picking 'emitterlegalname' (score: 1.00) over ['emitterfantasyname'(0.95)]
```

**Final Summary**:
```
[SUMMARY] Schema match for 'invoices':
  ✓ Matched: 12 columns
  ⚠ Needs review: 3 columns
  ✗ Unmatched: 5 columns

  Matched columns:
    'emitterlegalname' → 'emitter_nome' (score: 1.00)
    'receiverlegalname' → 'receiver_nome' (score: 1.00)
    ...
```

---

### 5. **Loud Warnings and Elegant Failures** ✅
**File**: [etl_service_v2.py:335-418](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L335-L418)

#### Schema Matching Phase:

**Success Case**:
```
================================================================================
✅ Schema mapping SUCCESS!
  ✓ All 45 columns mapped successfully
  ⚠ 3 columns flagged for review (lower confidence)
================================================================================
```

**Incomplete Match**:
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
⚠️  WARNING: Schema matching incomplete!
  ✓ Mapped: 40 columns
  ⚠ Needs review: 3 columns
  ✗ UNMATCHED: 2 columns

  Unmatched columns (will NOT be available in analytics):
    - unknown_field_1
    - unknown_field_2
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

**Missing Critical Columns**:
```
################################################################################
❌ CRITICAL ERROR: Key columns missing from mapping!
  Missing canonical columns: ['emitter_nome', 'receiver_nome']
  These columns are REQUIRED for analytics but were not matched.
  Check if source columns exist in BigQuery or if aliases need updating.
################################################################################
```

**Complete Failure**:
```
################################################################################
❌ CRITICAL ERROR: Schema matching failed completely!
  Error: KeyError: 'invoices'
  Impact: No column mapping will be available - analytics will likely FAIL
  Fallback: Using empty mapping (analytics will use column names as-is)
################################################################################
```

#### Persistence Phase:
**File**: [etl_service_v2.py:493-537](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L493-L537)

**Success**:
```
================================================================================
[PERSISTENCE] Saving data source to client_data_sources
  client_id: e0e9c949-18fe-4d9a-9295-d5dfb2cc9723
  credential_id: 42
  resource_type: invoices
  storage_location: bigquery.c_e0e9c949_invoices
  column_mapping entries: 45
  Sample mappings (first 10):
    'emitterlegalname' → 'emitter_nome'
    'receiverlegalname' → 'receiver_nome'
    'id_operatorinvoice' → 'order_id'
    ...
    ... and 35 more
================================================================================
✅ Successfully persisted data source to client_data_sources
```

**Empty Mapping Warning**:
```
================================================================================
[PERSISTENCE] Saving data source to client_data_sources
  ...
  column_mapping entries: 0
  ⚠️  WARNING: column_mapping is EMPTY! Analytics will likely fail.
================================================================================
```

**Persistence Failure**:
```
################################################################################
❌ CRITICAL ERROR: Failed to persist to client_data_sources!
  Error: relation "client_data_sources" does not exist
  Impact: Analytics API will NOT be able to find this data source
  This is a FATAL error - ETL cannot continue
################################################################################
```

---

## Testing Recommendations

### 1. **Test Schema Matcher Directly**

Create a test script to verify the matcher works correctly:

```python
from services.data_ingestion_api.src.data_ingestion_api.services.schema_matcher_service import schema_matcher

# Test with actual BigQuery columns
source_columns = [
    "emitterlegalname",
    "receiverlegalname",
    "id_operatorinvoice",
    "price_operatorinvoice",
    "unknown_column_xyz"
]

result = schema_matcher.auto_match(source_columns, "invoices")

print(f"Matched: {result.matched}")
print(f"Unmatched: {result.unmatched}")
print(f"Needs review: {result.needs_review}")

# Expected output:
# Matched: {
#   'emitterlegalname': 'emitter_nome',
#   'receiverlegalname': 'receiver_nome',
#   'id_operatorinvoice': 'order_id',
#   'price_operatorinvoice': 'valor_total_emitter'
# }
# Unmatched: ['unknown_column_xyz']
```

### 2. **Run ETL with Verbose Logging**

Set log level to INFO or DEBUG:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Then trigger a sync and watch for:
- ✓ Green checkmarks for successful matches
- ⚠ Warnings for conflicts or low-confidence matches
- ✗ Red X for failed matches
- Critical column verification

### 3. **Verify Persistence**

After ETL completes, query the database:

```sql
SELECT
    client_id,
    resource_type,
    column_mapping,
    jsonb_object_keys(column_mapping) as source_columns
FROM client_data_sources
WHERE client_id = 'your-client-id'
  AND resource_type = 'invoices';
```

**Expected**:
```json
{
  "emitterlegalname": "emitter_nome",
  "receiverlegalname": "receiver_nome",
  ...
}
```

### 4. **Test Analytics API**

After successful sync, query the Analytics API and check logs for:

```
[SILVER] Querying foreign table: bigquery.c_e0e9c949_invoices
  Reverse mapping applied:
    emitter_nome → emitterlegalname
    receiver_nome → receiverlegalname
  SELECT "emitterlegalname" AS emitter_nome,
         "receiverlegalname" AS receiver_nome
  FROM bigquery.c_e0e9c949_invoices
```

---

## Known Issues / Edge Cases

### 1. **Multiple Columns Mapping to Same Canonical**

**Example**: Both `emitterlegalname` and `emitterfantasyname` exist in source
- **Solution**: New logic picks the highest similarity score
- **Logged**: Warning shows which column was chosen and which was rejected

### 2. **Column Exists But Not Mapped**

**Example**: Source has `emitterlegalname` but it's not in alias list
- **Before**: Would fail silently or use low-confidence fuzzy match
- **After**: Loud warning about unmatched column + critical column check

### 3. **Completely Empty Mapping**

**Example**: Schema matching crashes or returns nothing
- **Before**: Silent failure, analytics API breaks later
- **After**: Critical error logged, empty mapping used as fallback, clear impact statement

---

## Files Modified

1. **[schema_matcher_service.py](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py)**
   - Removed `import re` (unused)
   - Simplified `normalize_column_name()` to only lowercase
   - Refactored `find_best_match()` to combine Stage 1 & 2
   - Added comprehensive logging throughout
   - Rewrote `auto_match()` with 3-pass algorithm for conflict resolution

2. **[etl_service_v2.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py)**
   - Added loud warnings for schema matching results
   - Added critical column verification
   - Added detailed persistence logging
   - Added try-catch with clear error messages
   - Made registry persistence non-fatal with warnings

---

## Next Steps

1. **Run the ETL sync** and observe the logs
2. **Verify the output** includes:
   - `emitterlegalname → emitter_nome` mapping
   - `receiverlegalname → receiver_nome` mapping
3. **Check database** that `column_mapping` in `client_data_sources` contains these mappings
4. **Test Analytics API** to ensure queries use the correct source column names
5. **Review any warnings** about unmatched or conflicting columns

---

## Summary

All requested improvements have been implemented:

- ✅ **Simplified normalization**: Only lowercase (minimal changes)
- ✅ **Removed redundant stages**: Combined Stage 1 & 2
- ✅ **Improved duplicate handling**: Use highest similarity score
- ✅ **Added comprehensive logging**: Visual indicators, structured output
- ✅ **Loud warnings and elegant failures**: Clear error messages, non-blocking where appropriate

The schema matcher should now be much more reliable and easier to debug. All failures are logged loudly with clear impact statements, but the ETL pipeline is resilient to non-critical failures.
