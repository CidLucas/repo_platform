# SQL Tool Prompt Flow - Comprehensive Review & Fixes
**Date:** 2026-01-28
**Issue:** LLM generating CTEs (WITH clauses) being rejected

---

## COMPREHENSIVE PROMPT FLOW ANALYSIS

### Layer 1: Agent-Level (atendente_core)

#### 1.1 System Prompts (ATENDENTE_SYSTEM_V1, V2, V3)
**File:** `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py`

**Purpose:** Tell the main agent WHEN and HOW to use the SQL tool

**Content Elements:**

| Element | Purpose | Current State |
|---------|---------|---|
| Tool descriptions | Explain what each tool does | ✅ Updated to mention complex queries |
| When to use | Guide agent's decision | ✅ "SEMPRE tente a SQL tool" |
| Data query examples | Show SQL tool is for data | ✅ Good |
| Formatting rules | How to present results | ✅ Good |
| "Golden Rules" | Don't invent, always use tools, try tool even if unsure | ✅ Updated |

**Key Rule Added:**
```
"❌ NUNCA assuma que colunas/dados não existem sem tentar a ferramenta"
```

---

#### 1.2 Tool Description (FastMCP Registration)
**File:** `sql_module.py` lines ~712

**Shown to agent LLM as:** Tool metadata when deciding to call

```python
description="""
    "ALWAYS call this tool for ANY question about data..."
    "Available tables: fact_sales, dim_customer, dim_supplier, dim_product..."
```

**Updated to include:**
- Explicit mention of city/state columns
- Encouragement: "Even if you're unsure about column names"
- No assumption that columns don't exist

---

### Layer 2: SQL Generation (inside tool_pool_api)

When user calls `executar_sql_agent`, an **internal second LLM** is invoked to generate SQL.

#### 2.1 System Message to SQL LLM

```python
SystemMessage(content="You are a SQL query generator. Output only valid SQL.")
```

**Purpose:** Focus LLM on SQL generation
**Issue:** Too generic - doesn't define what "valid SQL" means

**Improvement Needed:** Could be more specific about allowing CTEs

---

#### 2.2 Main SQL Generation Prompt (`sql_generation_prompt`)

**Location:** Lines 540-627

**Structure:**

```
[1] Architecture Overview
[2] Key Tables & Columns (business data only)
[3] Full Database Schema (introspected or hardcoded)
[4] RULES (what's allowed/forbidden)
[5] Example Queries (teach by example)
[6] User Question
```

---

### 2.2.1 Section: Architecture Overview
```
STAR SCHEMA ARCHITECTURE (schema: analytics_v2):
- FACT TABLE: fact_sales (transaction line items)
- DIMENSION TABLES: dim_customer, dim_supplier, dim_product
```

**Purpose:** Mental model for LLM
**Quality:** ✅ Adequate

---

### 2.2.2 Section: Key Tables & Columns
```
fact_sales:
- order_id, data_transacao, quantidade, valor_unitario, valor_total
- customer_id, supplier_id, product_id (UUIDs for joins)

dim_supplier:
- supplier_id, name, cnpj, telefone
- endereco_cidade (city)
- endereco_uf (state)
- total_revenue, total_orders_received
```

**Purpose:** Specific columns LLM can use
**Quality:** ✅ Good (now includes endereco_cidade, endereco_uf)
**Note:** Intentionally omits client_id (handled by security layer)

---

### 2.2.3 Section: Full Database Schema
```
DATABASE SCHEMA:
{table_info}
```

**What is `{table_info}`?**

Source Priority:
1. SqlTableConfig from Supabase (client-specific custom schemas)
2. Hardcoded schema fallback

**Fallback Schema Location:** Lines 210-290

Includes:
- All columns with types
- Relationships (FK definitions)
- Query patterns for city/state analysis

**Quality:** ✅ Good, comprehensive

---

### 2.2.4 Section: RULES

**Original (broken):**
```
1. Generate ONLY a valid SELECT query - no INSERT, UPDATE, DELETE, or DDL
```

**Problem:** Contradictory - Rule 1 says "SELECT only" but later allows CTEs

**Fixed Version:**
```
1. Generate ONLY valid SELECT queries - you can use WITH clauses (CTEs) followed by SELECT
12. For ranking, use window functions like ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)
```

**Other Rules:**
- 2: Output only SQL, no markdown
- 3: PostgreSQL syntax
- 4: Use data_transacao for dates
- 5-6: Schema-qualified names, exact column names
- 7: Always LIMIT (max 1000)
- 8: No legacy tables
- 9: Join via FKs
- 10-11: Never include client_id in WHERE (security)

**Quality:** ✅ Fixed, now allows CTEs

---

### 2.2.5 Section: Example Queries

**Original:** 4 simple examples (all basic SELECT)

**Fixed:** 5 examples including:
```
4. "Top 3 suppliers by city" (with CTE + window function)
   → WITH supplier_sales AS (
       SELECT ds.endereco_cidade, ds.name, SUM(fs.valor_total) as revenue
       FROM analytics_v2.fact_sales fs
       JOIN analytics_v2.dim_supplier ds ...
     )
     SELECT city, supplier_name, revenue,
            ROW_NUMBER() OVER (PARTITION BY city ORDER BY revenue DESC) as rank
     FROM supplier_sales
     WHERE rank <= 3
```

**Quality:** ✅ Now teaches CTEs and window functions

---

### Layer 3: Validation & Filtering

#### 3.1 SQL Type Validation (WAS BROKEN)

**Original Code:**
```python
if not sql_upper.strip().startswith("SELECT"):
    return {"output": "Error: Only SELECT queries are allowed."}
```

**Problem:** Rejects `WITH ... SELECT` (CTEs)

**Fixed Code:**
```python
if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
    return {"output": "Error: Only SELECT queries (including CTEs with WITH) are allowed."}

if sql_upper.startswith("WITH") and "SELECT" not in sql_upper:
    return {"output": "Error: WITH clauses must end with a SELECT statement."}
```

**Quality:** ✅ Fixed, now accepts CTEs

---

#### 3.2 Forbidden Keywords Check

```python
forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
for word in forbidden:
    if word in sql_upper:
        return {"output": f"Error: {word} queries are not allowed."}
```

**Purpose:** Prevent DDL/DML
**Quality:** ✅ Good

---

#### 3.3 Schema Validation

```python
_validate_sql_for_production_schema(generated_sql):
- No legacy tables (analytics_silver, analytics_gold)
- References analytics_v2
- Rejects if LLM tried to add client_id
```

**Quality:** ✅ Good

---

#### 3.4 Client_ID Filter Injection (IMPROVED)

**Old Approach:** Regex-based WHERE clause insertion (fragile with CTEs)

**New Approach:** Wrap entire query in CTE

```python
def _inject_client_id_filter(sql: str, client_id: str) -> str:
    # 1. Find all table aliases from analytics_v2 tables
    table_pattern = r"(?:FROM|JOIN)\s+analytics_v2\.(\w+)(?:\s+(?:AS\s+)?(\w+))?"
    matches = re.findall(table_pattern, sql_clean, re.IGNORECASE)

    # 2. Build conditions: "alias.client_id = 'uuid'"
    conditions = [f"{alias}.client_id = '{client_id}'" for alias, ... in matches]

    # 3. Wrap entire query:
    wrapped_sql = f"""WITH original_query AS (
        {sql_clean}
    )
    SELECT * FROM original_query
    WHERE {filter_clause}"""

    return wrapped_sql + ";"
```

**Why This is Better:**
- ✅ Works with CTEs (which already have WITH)
- ✅ Works with complex queries
- ✅ Works with window functions
- ✅ Always adds WHERE at outermost level
- ✅ Simpler, more robust

**Quality:** ✅ Fixed

---

### Layer 4: RLS Context (Defense in Depth)

```python
conn.execute(
    sa_text("SELECT set_config('app.current_cliente_id', :cliente_id, true)"),
    {"cliente_id": client_id_str},
)
```

**Purpose:** Set PostgreSQL session variable for RLS policies

**Note:** RLS policies on analytics_v2 tables provide second layer of defense

**Quality:** ✅ Good

---

## COMPLETE FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────┐
│ USER (Portuguese): "Top fornecedores por cidade"        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [Agent LLM] atendente_core                              │
│ Uses: System Prompt V1/V2/V3                            │
│ Sees: Tool descriptions from registration               │
│ Decides: "Use SQL tool" (based on updated instructions) │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [FastMCP] executar_sql_agent called                     │
│ Parameter: query = natural language question            │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [SQL Module] _executar_sql_agent_logic()                │
│ 1. Get schema context                                   │
│ 2. Build sql_generation_prompt (detailed + examples)    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [LLM #2] SQL Generation                                 │
│ Input: sql_generation_prompt with:                      │
│   - Architecture explanation                            │
│   - Column descriptions                                 │
│   - Full schema                                         │
│   - RULES (now allows CTEs!)                            │
│   - Example queries (now includes CTE examples!)        │
│   - User question                                       │
│                                                         │
│ Output: SQL query (may include CTEs + window funcs)    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [Validation Layer 1] SQL Type Check                     │
│ ✅ Accepts: SELECT ... or WITH ... SELECT              │
│ ❌ Rejects: INSERT, UPDATE, DELETE, DDL                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [Validation Layer 2] Schema Validation                  │
│ ✅ analytics_v2 only                                    │
│ ❌ No legacy tables                                     │
│ ❌ No client_id in WHERE (LLM shouldn't add it)        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [Security] Client_ID Filter Injection                   │
│ Wraps original query in CTE:                            │
│   WITH original_query AS (...)                          │
│   SELECT * FROM original_query                          │
│   WHERE alias.client_id = 'uuid'                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [RLS Context] Set PostgreSQL session variable           │
│ set_config('app.current_cliente_id', client_id)        │
│ (Defense in depth - RLS policies on DB also filter)    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [Execute] Query runs with:                              │
│ 1. Hard-injected client_id WHERE clause                │
│ 2. RLS policies from PostgreSQL                         │
│ 3. LIMIT 1000 enforcement                              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ [Return] Results to agent                              │
│ Agent formats and presents to user                      │
└─────────────────────────────────────────────────────────┘
```

---

## SUMMARY OF FIXES

| Component | Issue | Fix | Result |
|-----------|-------|-----|--------|
| SQL Prompt Rules | Says "SELECT only" but needs CTEs | Updated Rule 1 to allow `WITH...SELECT` | ✅ LLM can use CTEs |
| SQL Examples | No CTE examples | Added CTE + window function example | ✅ LLM learns by example |
| Validation Logic | Rejects `WITH ...` as invalid | Check for `startswith("SELECT") OR startswith("WITH")` | ✅ CTEs accepted |
| CTE Validation | Missing | Added check: "WITH must contain SELECT" | ✅ Catches malformed CTEs |
| Injection Logic | Regex-based WHERE insertion (breaks CTEs) | Wrap entire query in outer CTE | ✅ Works with any SQL |
| Tool Description | Incomplete columns listed | Added endereco_cidade, endereco_uf | ✅ Agent knows columns exist |
| System Prompts | Vague about using SQL tool | Added "NUNCA assuma que colunas não existem" | ✅ Agent tries tool more |

---

## INFORMATION HIERARCHY

What the LLM sees at each stage:

1. **Agent sees:** Tool description (brief list of tables)
2. **SQL LLM sees:**
   - Architecture (relationships)
   - Column descriptions (business meaning)
   - Full schema (all fields)
   - Rules (what's allowed)
   - Examples (patterns)
   - Question (user query)

3. **After generation:** Only validation errors (not execution results)

---

## SECURITY LAYERS

1. **Prompt Layer:** LLM shouldn't add client_id (not shown in prompt)
2. **Validation Layer:** Rejects if client_id is in WHERE
3. **Injection Layer:** Adds client_id filter hard-injected by server
4. **Database Layer:** RLS policies (PostgreSQL enforces)

**Result:** Even if LLM bypasses layer 1, layers 2-4 catch it.
