# Schema Matching Flow - Complete Analysis

## Overview

This document provides a detailed analysis of the complete schema matching flow from BigQuery data ingestion through column mapping to the final `column_mapping` field stored in `client_data_sources`.

---

## 1. Entry Point: ETL Service V2 (`etl_service_v2.py`)

### Function: `run_etl_job()`
**Location**: [etl_service_v2.py:115-544](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L115-L544)

**Purpose**: Orchestrates the entire ETL process for BigQuery data ingestion

**Flow**:
1. **Load Credentials** (Lines 152-188):
   - Fetches BigQuery credentials from `credencial_servico_externo` table
   - Extracts: `project_id`, `dataset_id`, `table_name`, `location`, `service_account_json`

2. **Setup BigQuery Server** (Lines 189-306):
   - Creates/validates foreign server connection via `bigquery_wrapper_service`
   - Handles server recreation if parameters change

3. **Discover BigQuery Schema** (Lines 315-333):
   - Calls `_fetch_bigquery_schema()` to get actual column names from BigQuery
   - Returns list of `{"name": "column_name", "type": "postgres_type"}`

4. **Build Schema Mapping** (Lines 336-378):
   ```python
   source_column_names = [c["name"] for c in foreign_table_columns]  # Extract just column names
   schema_type_for_match = _infer_schema_type(resource_type)         # "invoices", "products", etc.
   match_result = schema_matcher.auto_match(source_column_names, schema_type_for_match)
   mapping_dict = match_result.matched  # {"emitterlegalname": "emitter_nome", ...}
   ```

5. **Store Mapping** (Lines 447-468):
   ```python
   column_mapping_for_ds = mapping_dict  # The computed mapping
   await supabase_client.upsert(
       "client_data_sources",
       {
           "column_mapping": column_mapping_for_ds,  # ← THIS IS THE KEY FIELD
           "source_columns": source_columns_jsonb,
           ...
       }
   )
   ```

**Key Issue**: The `mapping_dict` from `schema_matcher.auto_match()` should contain mappings like:
```json
{
  "emitterlegalname": "emitter_nome",
  "receiverlegalname": "receiver_nome"
}
```

But something is going wrong between the matching and storage phases.

---

## 2. Schema Discovery: `_fetch_bigquery_schema()`

### Function: `_fetch_bigquery_schema()`
**Location**: [etl_service_v2.py:32-86](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L32-L86)

**Purpose**: Fetches actual column names and types from BigQuery using REST API

**Process**:
1. Uses Google service account to authenticate
2. Calls BigQuery REST API: `GET /projects/{project}/datasets/{dataset}/tables/{table}`
3. Parses `schema.fields` to extract column definitions
4. Converts BigQuery types to PostgreSQL types
5. **Normalizes column names to lowercase** (Line 76):
   ```python
   columns.append({"name": name.lower(), "type": pg_type})
   ```

**Output Example**:
```python
[
  {"name": "emitterlegalname", "type": "text"},      # Lowercase!
  {"name": "receiverlegalname", "type": "text"},     # Lowercase!
  {"name": "id", "type": "text"},
  ...
]
```

**Critical Point**: Column names are normalized to **lowercase** here. This means the schema matcher receives lowercase column names.

---

## 3. Schema Type Inference: `_infer_schema_type()`

### Function: `_infer_schema_type()`
**Location**: [etl_service_v2.py:89-109](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L89-L109)

**Purpose**: Maps the user-provided `resource_type` to a canonical schema type

**Logic**:
```python
normalized = (resource_type or "").lower()
if normalized in schema_matcher.get_supported_types():
    return normalized  # Direct match
if "invoice" in normalized:
    return "invoices"  # Fuzzy match
# ... other fuzzy matches
```

**Output**: One of `["invoices", "orders", "products", "customers", "inventory", "categories"]`

---

## 4. Core Matching Engine: `SchemaMatcherService`

### 4.1 Configuration Data

#### Canonical Schema Definition
**Location**: [schema_matcher_service.py:77-195](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L77-L195)

Defines the target columns for each resource type:
```python
CANONICAL_SCHEMAS = {
    "invoices": [
        "order_id",
        "data_transacao",
        "emitter_nome",      # ← Target canonical name
        "emitter_cnpj",
        "receiver_nome",     # ← Target canonical name
        "receiver_cpf_cnpj",
        ...
    ],
    ...
}
```

#### Column Aliases
**Location**: [schema_matcher_service.py:198-262](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L198-L262)

Maps known variations to canonical names:
```python
COLUMN_ALIASES = {
    "emitter_nome": ["emitterlegalname", "emitterfantasyname", "nome_emitter"],
    "receiver_nome": ["receiverlegalname", "receiverfantasyname", "nome_receiver"],
    ...
}
```

**Key Point**: The aliases include `"emitterlegalname"` and `"receiverlegalname"` which should match the lowercase column names from BigQuery.

---

### 4.2 Alias Cache Builder

#### Function: `_build_alias_cache()`
**Location**: [schema_matcher_service.py:381-391](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L381-L391)

**Purpose**: Pre-computes a reverse lookup map for fast alias matching

**Process**:
```python
for schema_type, columns in self.CANONICAL_SCHEMAS.items():
    self._alias_to_canonical[schema_type] = {}
    for canonical in columns:
        # Add canonical name itself
        self._alias_to_canonical[schema_type][canonical.lower()] = canonical

        # Add all aliases
        if canonical in self.COLUMN_ALIASES:
            for alias in self.COLUMN_ALIASES[canonical]:
                self._alias_to_canonical[schema_type][alias.lower()] = canonical
```

**Result for "invoices"**:
```python
{
    "emitter_nome": "emitter_nome",
    "emitterlegalname": "emitter_nome",     # ← Alias mapping
    "emitterfantasyname": "emitter_nome",
    "receiver_nome": "receiver_nome",
    "receiverlegalname": "receiver_nome",   # ← Alias mapping
    ...
}
```

**Verification Point**: Check if the cache is built correctly. The aliases should be lowercased during cache construction.

---

### 4.3 Column Name Normalization

#### Function: `normalize_column_name()`
**Location**: [schema_matcher_service.py:442-473](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L442-L473)

**Purpose**: Normalizes column names for consistent comparison

**Transformations**:
1. Convert to lowercase
2. Remove special characters (keep underscores)
3. Remove duplicate underscores
4. Strip leading/trailing underscores
5. **Remove common prefixes** (product_, order_, customer_, etc.)
6. Remove leading numbers

**Example**:
```python
Input:  "EmitterLegalName"
Step 1: "emitterlegalname"        # Lowercase
Step 2: "emitterlegalname"        # No special chars
Step 3: "emitterlegalname"        # No duplicates
Step 4: "emitterlegalname"        # No leading/trailing _
Step 5: "emitterlegalname"        # No common prefix to remove
Step 6: "emitterlegalname"        # No leading numbers
Output: "emitterlegalname"
```

**Critical Issue**: The normalization does NOT add underscores or change the structure - it only cleans. So `"emitterlegalname"` stays as `"emitterlegalname"`.

---

### 4.4 Main Matching Logic

#### Function: `auto_match()`
**Location**: [schema_matcher_service.py:602-675](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L602-L675)

**Purpose**: Main entry point for automatic schema matching

**Process**:
```python
def auto_match(source_columns, schema_type, high_threshold=0.85, medium_threshold=0.70):
    canonical_columns = self.CANONICAL_SCHEMAS[schema_type]  # e.g., ["emitter_nome", ...]
    result = SchemaMatchResult()
    used_canonicals = set()  # Track already-matched columns

    for source_col in source_columns:  # e.g., "emitterlegalname"
        # Find best match
        best_match, score = self.find_best_match(source_col, canonical_columns, schema_type)

        # Avoid duplicates
        if best_match and best_match in used_canonicals:
            remaining = [c for c in canonical_columns if c not in used_canonicals]
            if remaining:
                best_match, score = self.find_best_match(source_col, remaining, schema_type)

        # Categorize by confidence
        if score >= high_threshold and best_match:
            result.matched[source_col] = best_match  # {"emitterlegalname": "emitter_nome"}
            used_canonicals.add(best_match)
        elif score >= medium_threshold and best_match:
            result.matched[source_col] = best_match
            result.needs_review.append(source_col)
            used_canonicals.add(best_match)
        else:
            result.unmatched.append(source_col)

    return result
```

**Key Output**: `result.matched` dictionary with format:
```python
{
    "emitterlegalname": "emitter_nome",
    "receiverlegalname": "receiver_nome",
    ...
}
```

---

#### Function: `find_best_match()`
**Location**: [schema_matcher_service.py:488-561](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L488-L561)

**Purpose**: 4-stage matching strategy to find the best canonical column for a source column

**Stages**:

**STAGE 1: Exact Alias Match** (Lines 512-518)
```python
normalized_source = self.normalize_column_name(source_column)  # "emitterlegalname"
alias_cache = self._alias_to_canonical.get(schema_type, {})
if normalized_source in alias_cache:  # Check if "emitterlegalname" is in cache
    canonical = alias_cache[normalized_source]  # Get "emitter_nome"
    if canonical in canonical_columns:
        return canonical, 1.0  # Perfect match!
```

**This is where the match should happen for `emitterlegalname` → `emitter_nome`**

**STAGE 2: Exact Normalized Match** (Lines 521-525)
```python
for canonical in canonical_columns:
    normalized_canonical = self.normalize_column_name(canonical)
    if normalized_source == normalized_canonical:
        return canonical, 1.0
```

**STAGE 3: Type-Aware Fuzzy Match** (Lines 528-545)
- Infers data type of source column
- Filters canonical columns by compatible type
- Performs fuzzy matching only within type-compatible columns
- Returns match if score >= 0.6

**STAGE 4: Global Fuzzy Match with Penalty** (Lines 547-560)
- Fuzzy match across all columns (fallback)
- Penalizes type-incompatible matches by 30%

---

#### Function: `_fuzzy_match_in_columns()`
**Location**: [schema_matcher_service.py:563-600](services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py#L563-L600)

**Purpose**: Performs fuzzy string matching using `difflib.SequenceMatcher`

**Process**:
```python
def _fuzzy_match_in_columns(normalized_source, candidate_columns):
    best_match = None
    best_score = 0.0

    for canonical in candidate_columns:
        normalized_canonical = self.normalize_column_name(canonical)

        # Direct similarity
        score = self.calculate_similarity(normalized_source, normalized_canonical)

        # Check aliases too
        if canonical in self.COLUMN_ALIASES:
            for alias in self.COLUMN_ALIASES[canonical]:
                normalized_alias = self.normalize_column_name(alias)
                alias_score = self.calculate_similarity(normalized_source, normalized_alias)
                score = max(score, alias_score)

        if score > best_score:
            best_score = score
            best_match = canonical

    return best_match, best_score
```

---

## 5. Persistence: Schema Registry Service

### Function: `save_mapping()`
**Location**: [schema_registry_service.py:90-170](services/data_ingestion_api/src/data_ingestion_api/services/schema_registry_service.py#L90-L170)

**Purpose**: Saves the schema mapping to `data_source_mappings` table (best-effort)

**Note**: This table may not exist (Option B removed it), so failures are handled gracefully. The important persistence happens in `client_data_sources.column_mapping`.

---

## 6. Final Storage in `client_data_sources`

**Location**: [etl_service_v2.py:453-468](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L453-L468)

```python
column_mapping_for_ds = mapping_dict if mapping_dict else None

await supabase_client.upsert(
    "client_data_sources",
    {
        "client_id": client_id,
        "credential_id": int(credential_id),
        "source_type": "bigquery",
        "resource_type": resource_type,
        "storage_type": "foreign_table",
        "storage_location": foreign_table_name,
        "column_mapping": column_mapping_for_ds,  # ← THE CRITICAL FIELD
        "source_columns": source_columns_jsonb,
        "sync_status": "active",
        "last_synced_at": "now()",
    },
    on_conflict="client_id,source_type,resource_type"
)
```

**Expected `column_mapping` Format**:
```json
{
  "emitterlegalname": "emitter_nome",
  "receiverlegalname": "receiver_nome",
  "id_operatorinvoice": "order_id",
  ...
}
```

---

## 7. Analytics API Consumption

**Location**: [postgres_repository.py](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)

The Analytics API uses `column_mapping` to translate canonical names to source names:

```python
def get_silver_dataframe(self, client_id: str, resource_type: str) -> pd.DataFrame:
    # Get data source info
    data_source = self._get_data_source(client_id, resource_type)
    column_mapping = data_source.get("column_mapping", {})  # Load mapping

    # Build reverse mapping: canonical → source
    reverse_mapping = {canonical: source for source, canonical in column_mapping.items()}

    # Generate SELECT clause
    selected_cols = []
    for canonical in REQUIRED_COLUMNS:
        source_col = reverse_mapping.get(canonical, canonical)  # Fallback to canonical if not mapped
        selected_cols.append(f'"{source_col}" AS {canonical}')

    query = f"SELECT {', '.join(selected_cols)} FROM {foreign_table}"
```

**The Problem**: If `column_mapping` is missing `"emitterlegalname": "emitter_nome"`, then:
- `reverse_mapping["emitter_nome"]` returns KeyError or None
- Falls back to using `"emitter_nome"` as source column name
- But the BigQuery table has `"emitterlegalname"`, not `"emitter_nome"`
- Result: Column not found in SELECT query

---

## Diagnosis Points

### 1. **Is the alias cache built correctly?**
Check if `_build_alias_cache()` properly includes:
```python
self._alias_to_canonical["invoices"]["emitterlegalname"] == "emitter_nome"
```

### 2. **Is Stage 1 matching working?**
When `find_best_match("emitterlegalname", ...)` is called:
- Does `normalized_source` equal `"emitterlegalname"`?
- Does `alias_cache` contain key `"emitterlegalname"`?
- Does it return `("emitter_nome", 1.0)`?

### 3. **Is the match result stored correctly?**
Check if `match_result.matched` contains:
```python
{"emitterlegalname": "emitter_nome"}
```

### 4. **Is the mapping persisted correctly?**
Check if `column_mapping` in `client_data_sources` contains:
```json
{"emitterlegalname": "emitter_nome"}
```

### 5. **Is the mapping consumed correctly?**
Check if Analytics API's reverse mapping correctly translates:
```python
reverse_mapping["emitter_nome"] → "emitterlegalname"
```

---

## Suspected Root Cause

Based on your observation that `"emitter_nome": ["emitterlegalname"]` exists in `COLUMN_ALIASES`, but the columns are missing from the mapped view, I suspect **one of these issues**:

### Hypothesis A: Alias Cache Not Built Correctly
The `_build_alias_cache()` might not be lowercasing the aliases when building the cache:

```python
# Current (potentially broken):
for alias in self.COLUMN_ALIASES[canonical]:
    self._alias_to_canonical[schema_type][alias.lower()] = canonical  # ← Is .lower() called?
```

**Check**: Add logging to verify the cache contents.

### Hypothesis B: Normalization Breaking the Match
The `normalize_column_name()` might be modifying the column name in a way that breaks the alias match:

```python
normalized = "emitterlegalname"  # From BigQuery
alias_in_cache = "emitterlegalname"  # Expected in cache
```

If normalization adds/removes characters, the match fails.

### Hypothesis C: Mapping Not Persisted
The `mapping_dict` might be correctly computed but not stored in `client_data_sources.column_mapping` due to:
- Database error silently caught
- Wrong variable passed to upsert
- JSONB serialization issue

### Hypothesis D: Duplicate Canonical Columns
If multiple source columns match the same canonical column (e.g., both `emitterlegalname` and `emitterfantasyname` match `emitter_nome`), the `used_canonicals` set prevents the second match, potentially skipping valid mappings.

---

## Next Steps for Debugging

1. **Add verbose logging** to `_build_alias_cache()` to verify cache contents
2. **Add verbose logging** to `find_best_match()` Stage 1 to see if alias lookup succeeds
3. **Add verbose logging** after `auto_match()` to inspect `match_result.matched`
4. **Query database** to check actual `column_mapping` value in `client_data_sources`
5. **Test isolated** schema matcher with sample data:
   ```python
   matcher = SchemaMatcherService()
   result = matcher.auto_match(["emitterlegalname", "receiverlegalname"], "invoices")
   print(result.matched)  # Should include both mappings
   ```

---

## Summary

The schema matching flow is a **5-stage pipeline**:

1. **BigQuery Schema Discovery** → Lowercase column names
2. **Schema Type Inference** → Map resource_type to canonical schema
3. **Auto Matching** → 4-stage matching (alias → exact → fuzzy → fallback)
4. **Persistence** → Store in `client_data_sources.column_mapping`
5. **Consumption** → Analytics API reverse-maps canonical → source

The issue is likely in **Stage 3 (Auto Matching)** where the alias lookup should work but might not be due to:
- Cache not built correctly
- Normalization breaking the match
- Duplicate prevention logic skipping valid matches

The fix should focus on ensuring `emitterlegalname` and `receiverlegalname` are successfully matched to their canonical names and stored in `column_mapping`.
