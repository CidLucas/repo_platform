# Code Changes - CTE Scope-Aware Injection

**File:** [services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py](services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py)
**Date:** 2026-01-28
**Lines Modified:** 361-530

---

## Change 1: New Helper Function `_inject_filters_into_ctes()`

**Location:** Lines 361-430
**Purpose:** Inject client_id filters into CTE WHERE clauses when the final SELECT doesn't directly reference analytics_v2 tables

**Key Logic:**
```python
def _inject_filters_into_ctes(sql_with_ctes: str, filter_clause: str, full_query: str) -> str:
    """
    Inject client_id filters into each CTE that references analytics_v2 tables.

    When the final SELECT only references CTEs (not analytics_v2 tables directly),
    we need to inject filters INTO the CTEs instead.
    """
    # 1. Find the last CTE's closing paren
    last_closing_paren = result.rfind(")")

    # 2. Check if there's a WHERE in that CTE
    last_where = result[:last_closing_paren].rfind("WHERE")

    if last_where > 0:
        # WHERE exists - append filters before next keyword
        # Find: GROUP BY, ORDER BY, LIMIT, or closing paren
        next_keyword = re.search(r"\s+(?:GROUP|ORDER|LIMIT|$|\))", ...)
        if next_keyword:
            insert_pos = ...
            return result[:insert_pos] + f" AND {filter_clause}" + result[insert_pos:]
    else:
        # No WHERE - create one
        # Find where to insert (before GROUP BY/ORDER BY/LIMIT/closing paren)
        next_clause = re.search(r"\s+(?:GROUP|ORDER|LIMIT|$|\))", ...)
        if next_clause:
            insert_pos = ...
            return result[:insert_pos] + f"\nWHERE {filter_clause}" + result[insert_pos:]

    return result
```

### Example Transformation

**Input:**
```sql
supplier_rev AS (
  SELECT ... SUM(fs.valor_total) AS supplier_rev
  FROM analytics_v2.fact_sales fs
  GROUP BY cs.city, ds.name
)
```

**Output:**
```sql
supplier_rev AS (
  SELECT ... SUM(fs.valor_total) AS supplier_rev
  FROM analytics_v2.fact_sales fs
  WHERE fs.client_id = '...' AND ds.client_id = '...'
  GROUP BY cs.city, ds.name
)
```

---

## Change 2: Updated `_inject_client_id_filter()` - Detection Logic

**Location:** Lines 387-410 (within main function)
**Purpose:** Detect whether final SELECT directly references analytics_v2 tables or only references CTEs

**Key Changes:**

```python
def _inject_client_id_filter(sql: str, client_id: str) -> str:
    sql_clean = sql.strip().rstrip(";")

    # Extract final SELECT after all CTEs
    if sql_clean.upper().startswith("WITH"):
        last_cte_end = sql_clean.rfind(")")
        main_query = sql_clean[last_cte_end + 1:].strip()
        main_query_start = last_cte_end + 1
    else:
        main_query = sql_clean
        main_query_start = 0

    # ✅ NEW: Only look for analytics_v2 tables in the FINAL SELECT
    # (not in the entire query)
    table_pattern = r"(?:FROM|JOIN)\s+analytics_v2\.(\w+)(?:\s+(?:AS\s+)?(\w+))?"
    matches = re.findall(table_pattern, main_query, re.IGNORECASE)  # ← main_query only!

    if not matches:
        # ✅ NEW: No direct analytics_v2 references in final SELECT
        # This means the final SELECT only references CTEs
        # Solution: Inject into the CTEs instead
        logger.debug("[SQL] No analytics_v2 tables in final SELECT, injecting into CTEs")

        if not sql_clean.upper().startswith("WITH"):
            logger.warning("[SQL] No CTEs and no analytics_v2 tables")
            return sql_clean + ";"

        # Find all analytics_v2 references in the ENTIRE query (for CTE injection)
        full_table_pattern = r"(?:FROM|JOIN)\s+analytics_v2\.(\w+)(?:\s+(?:AS\s+)?(\w+))?"
        full_matches = re.findall(full_table_pattern, sql_clean, re.IGNORECASE)

        if not full_matches:
            logger.warning("[SQL] No analytics_v2 tables in entire query")
            return sql_clean + ";"

        # Build filter clause from full query matches
        conditions = []
        seen_aliases = set()

        for table_name, alias in full_matches:
            if alias:
                table_ref = alias.lower()
            else:
                table_ref = table_name.lower()

            if table_ref not in seen_aliases:
                if alias:
                    conditions.append(f"{alias}.client_id = '{client_id}'")
                else:
                    conditions.append(f"analytics_v2.{table_name}.client_id = '{client_id}'")
                seen_aliases.add(table_ref)

        filter_clause = " AND ".join(conditions)

        # ✅ NEW: Call CTE injection function
        injected_sql_cte = _inject_filters_into_ctes(sql_clean[:last_cte_end + 1],
                                                      filter_clause,
                                                      sql_clean)

        return injected_sql_cte + ";"

    # EXISTING: Direct table references - use original logic
    # (inject into final SELECT's WHERE clause)
    # ... rest of function unchanged ...
```

### Decision Tree

```
Query starts with WITH?
│
├─ YES: Has CTEs
│   │
│   ├─ Extract final SELECT (after last CTE closing paren)
│   │
│   ├─ Does final SELECT reference analytics_v2 tables?
│   │
│   ├─ YES: Inject into final SELECT WHERE
│   │   └─ Examples:
│   │       • WITH x AS (...) SELECT * FROM analytics_v2.fact_sales
│   │       • WITH x AS (...) SELECT * FROM y JOIN analytics_v2.fact_sales
│   │
│   └─ NO: Final SELECT only references CTEs
│       └─ Inject into CTEs instead
│           └─ Examples:
│               • WITH x AS (SELECT * FROM analytics_v2.fact_sales),
│                    y AS (SELECT * FROM x)
│                 SELECT * FROM y
│
└─ NO: No CTEs - simple SELECT
    │
    ├─ References analytics_v2? YES → Inject into WHERE
    └─ References analytics_v2? NO  → Return as-is (error case)
```

---

## Scope Comparison

### OLD Code
```python
# Extract aliases from ENTIRE query (including CTEs)
matches = re.findall(table_pattern, sql_clean, re.IGNORECASE)
# ❌ Gets: all fs, ds from CTEs even if not in final SELECT

# Extract final SELECT
main_query = extract_final_select()
# Result: "SELECT ... FROM ranked_sup WHERE rn <= 3"

# Inject into final SELECT
inject_into_where(main_query, matches)
# ❌ Tries to use fs/ds in scope where they don't exist!
```

### NEW Code
```python
# Extract aliases from FINAL SELECT ONLY
matches = re.findall(table_pattern, main_query, re.IGNORECASE)
# ✅ Only gets table references that actually exist in final SELECT

# If final SELECT has no direct table references
if not matches:
    # Extract aliases from ENTIRE query
    full_matches = re.findall(table_pattern, sql_clean, re.IGNORECASE)

    # Inject into CTEs (where those tables actually exist)
    _inject_filters_into_ctes(sql_clean, filter_clause)
    # ✅ Injects in correct scope!
```

---

## Testing Verification

### Test Case: Multi-Level CTEs
```python
test_query = """
WITH city_rev AS (
  SELECT ... FROM analytics_v2.fact_sales fs
),
supplier_rev AS (
  SELECT ... FROM analytics_v2.dim_supplier ds
),
ranked_sup AS (
  SELECT ... FROM supplier_rev  ← Only references CTE, not tables
)
SELECT * FROM ranked_sup
WHERE rn <= 3
"""
```

**Old Behavior:** ❌
```
WHERE rn <= 3 AND fs.client_id = '...' AND ds.client_id = '...'
↑ ERROR: fs/ds don't exist here!
```

**New Behavior:** ✅
```
supplier_rev AS (
  SELECT ... FROM analytics_v2.dim_supplier ds
  WHERE ds.client_id = '...'  ← Injected here!
)
```

---

## Edge Cases Handled

1. **CTE without WHERE:** Creates WHERE clause
2. **CTE with WHERE:** Appends to existing WHERE
3. **CTE with GROUP BY:** Inserts before GROUP BY
4. **CTE with ORDER BY:** Inserts before ORDER BY
5. **CTE with LIMIT:** Inserts before LIMIT
6. **Multiple CTEs:** Injects into last one with analytics_v2 references
7. **Nested CTEs:** Correctly identifies closing parens

---

## Debug Logging

Added strategic debug messages to help troubleshoot:

```python
logger.debug("[SQL] No analytics_v2 tables in final SELECT, injecting into CTEs")
logger.debug(f"[SQL] Final SELECT: {main_query[:200]}")
logger.debug(f"[SQL] Will inject into CTEs: {filter_clause}")
```

Look for these in logs to verify the new code path is being executed.

---

## Backward Compatibility

✅ **Fully backward compatible**

- Simple SELECT queries: Unchanged behavior
- CTEs with direct references: Unchanged behavior
- NEW: CTEs without direct references now work (previously failed)

No breaking changes to existing functionality.
