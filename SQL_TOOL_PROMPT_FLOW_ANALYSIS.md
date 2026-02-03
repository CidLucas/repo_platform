# SQL Tool Prompt Flow Analysis
**Date:** 2026-01-28
**Issue:** LLM generating CTEs (WITH clauses) being rejected as "not SELECT"

---

## 1. AGENT-LEVEL PROMPTS (atendente_core)

### 1.1 System Prompts (Templates)
These are defined in `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py`

**ATENDENTE_SYSTEM_V1, V2, V3** provide:
- **Purpose:** Tell agent WHEN and HOW to use SQL tool
- **Content:**
  - When to use: "For data questions: orders, sales, products, customers, analytics"
  - Instructions: "ALWAYS try SQL tool first, even if unsure about columns"
  - Formatting: How to display tabular data to user
  - Rules: Never invent data, always use tools, don't assume columns don't exist

**Problem:** These are good but don't tell agent that CTEs are valid/expected

### 1.2 Tool Registration Description
**File:** `sql_module.py` lines ~710

```python
mcp.tool(
    name="executar_sql_agent",
    description="""
    "ALWAYS call this tool for ANY question about data..."
    "Available tables in analytics_v2 schema:
    - fact_sales, dim_customer, dim_supplier, dim_product..."
```

**Purpose:** Quick reference for agent LLM - tells it WHAT data exists
**Current Issues:**
- Doesn't say CTEs are acceptable
- Doesn't mention that complex queries with CTEs are expected

---

## 2. SQL GENERATION LLM PROMPTS (inside tool_pool_api)

When user calls `executar_sql_agent`, internally there's a SECOND LLM call to generate SQL.

### 2.1 System Message
```python
SystemMessage(content="You are a SQL query generator. Output only valid SQL.")
```

**Purpose:** Keep LLM focused on SQL generation
**Issue:** Too vague - doesn't say what "valid SQL" means for this system

### 2.2 Main Generation Prompt (`sql_generation_prompt`)
**Location:** Lines 540-627 in sql_module.py

**Sections:**

#### A. Architecture Description
```
STAR SCHEMA ARCHITECTURE (schema: analytics_v2):
- FACT TABLE: fact_sales (transaction line items)
- DIMENSION TABLES: dim_customer, dim_supplier, dim_product
```
**Purpose:** Give LLM mental model of data structure
**Serves:** Helps LLM understand relationships and joins
**Adequate:** ✅ Yes

#### B. Column Descriptions by Table
```
fact_sales: order_id, data_transacao, quantidade, valor_unitario, valor_total...
dim_supplier: supplier_id, name, cnpj, telefone, endereco_cidade, endereco_uf...
```
**Purpose:** Detailed schema for LLM to write accurate queries
**Serves:** Tells LLM what columns exist and their types
**Adequate:** ✅ Yes (now includes endereco_cidade, endereco_uf)

#### C. Full Database Schema
```
DATABASE SCHEMA:
{table_info}
```
**Purpose:** Fallback to actual introspected or hardcoded schema
**Serves:** Ensures LLM has complete picture (handles custom columns from SqlTableConfig)
**Adequate:** ✅ Yes, but schema can be outdated

#### D. RULES Section
```
1. Generate ONLY a valid SELECT query - no INSERT, UPDATE, DELETE, or DDL
2. Output ONLY the SQL query, nothing else - no explanations, no markdown
3. Use proper SQL syntax for PostgreSQL
...
10. NEVER include client_id, UUIDs, or any ID columns in WHERE clauses
11. NEVER output or reference specific IDs, CPF, CNPJ...
```

**Purpose:** Security and output control
**Serves:**
- Rule 1: "ONLY SELECT" - **❌ WRONG! CTEs with WITH are also SELECT operations!**
- Rules 2-3: Formatting control
- Rules 10-11: Security (hide client_id)

**Issue:** Rule 1 says "ONLY SELECT" but CTEs (WITH...SELECT) are perfectly valid and expected for complex queries

#### E. Example Queries
```
1. Simple aggregations with WHERE
2. Date filtering with data_transacao
3. Joins with GROUP BY
4. Complex queries with JOINs
```

**Purpose:** Show LLM acceptable patterns
**Serves:** Teaching by example
**Issues:**
- All examples are simple SELECT queries
- No CTE examples
- No window function examples (but LLM generated ROW_NUMBER() OVER)

---

## 3. SCHEMA DEFINITIONS

### 3.1 Hardcoded Schema (`_get_hardcoded_analytics_v2_schema()`)
**Location:** Lines 210-290

**Content:**
- Complete table definitions with all columns
- Relationships (FK definitions)
- Query patterns (city/state analysis)
- Removes client_id from instructions (handled automatically)

**Purpose:** Fallback when SQLDatabase introspection fails
**Quality:** ✅ Good but could include CTE examples

### 3.2 Enriched Schema Context (`_get_enriched_schema_context()`)
**Location:** Lines 45-175

**Purpose:** Get schema from SqlTableConfig (database-managed configs)
**Falls back to:** Hardcoded schema if no configs found

---

## 4. SQL VALIDATION & REJECTION POINTS

### 4.1 SELECT-only Check (❌ THE PROBLEM)
```python
sql_upper = generated_sql.upper()
if not sql_upper.strip().startswith("SELECT"):
    logger.error(f"[SQL] Invalid SQL (not SELECT): {generated_sql}")
    return {"output": "Error: Only SELECT queries are allowed.", "sql": generated_sql}
```

**Location:** Lines 645-648
**Issue:** Rejects valid `WITH ... SELECT` queries (CTEs)
**Why happened:** LLM generated a CTE which is better SQL, but validation was too strict

### 4.2 Forbidden Keywords Check
```python
forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
for word in forbidden:
    if word in sql_upper:
        return {"output": f"Error: {word} queries are not allowed."}
```

**Location:** Lines 650-655
**Purpose:** Prevent DDL/DML queries
**Quality:** ✅ Good

### 4.3 Schema Validation (`_validate_sql_for_production_schema()`)
```python
- No legacy tables (analytics_silver, analytics_gold)
- References analytics_v2
- Rejects if LLM tried to add client_id (shouldn't happen)
```

**Location:** Lines 324-357
**Quality:** ✅ Good

---

## 5. CLIENT_ID INJECTION (`_inject_client_id_filter()`)
**Location:** Lines 361-419

**How it works:**
1. Parses query for table aliases (e.g., `FROM analytics_v2.fact_sales fs`)
2. Builds WHERE conditions: `fs.client_id = '{client_id}'`
3. Injects into query

**Issues:**
- Works with WHERE clauses
- Works with JOINs
- **BUT: If query starts with WITH (CTE), injection logic may not work correctly**

---

## 6. RLS CONTEXT SETTING
```python
conn.execute(
    sa_text("SELECT set_config('app.current_cliente_id', :cliente_id, true)"),
    {"cliente_id": client_id_str},
)
```

**Purpose:** Double-defense - RLS policies on DB also filter by client_id
**Quality:** ✅ Good

---

## FLOW DIAGRAM

```
User Question (Portuguese)
    ↓
[AGENT] atendente_core system prompt
    → "Use executar_sql_agent for data questions"
    → Tool description says "ALWAYS TRY THIS TOOL"
    ↓
[MCP TOOL] executar_sql_agent called
    ↓
[SQL_MODULE] _executar_sql_agent_logic()
    ↓
[LLM #2] SQL Generation with detailed prompt
    → SystemMessage: "You are a SQL query generator"
    → HumanMessage: Schema + Rules + Examples + Question
    → LLM generates SQL (may use CTEs!)
    ↓
[VALIDATION] Check if starts with "SELECT"
    ❌ REJECTS "WITH ... SELECT"
    ↓
[INJECTION] Add client_id filter
    ↓
[RLS] Set DB context
    ↓
[EXECUTE] Run query
```

---

## ROOT CAUSES

1. **Rule in prompt says "ONLY SELECT"** but allows CTEs in rules section
2. **Validation checks `startswith("SELECT")`** but CTEs start with "WITH"
3. **No CTE examples** to show LLM they're acceptable
4. **Injection logic** not tested with CTEs

---

## FIXES NEEDED

### Fix 1: Update SQL Generation Prompt
- Add CTEs to Rule 1
- Add CTE example with ROW_NUMBER() OVER
- Document when CTEs are needed (ranking, window functions)

### Fix 2: Update Validation
- Check if query starts with "SELECT" OR "WITH"
- OR check if it contains "SELECT" (simpler)
- Allow CTEs as long as they end with SELECT

### Fix 3: Test Injection with CTEs
- Verify that `_inject_client_id_filter()` works with WITH clauses
- May need to inject into first CTE or main SELECT

### Fix 4: System Messages
- Update agent prompt to mention "complex queries with CTEs are OK"
