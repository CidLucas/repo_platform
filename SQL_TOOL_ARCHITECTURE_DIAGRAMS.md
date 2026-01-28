# SQL Tool Data Flow - Architecture Diagrams

---

## 1. Full Request-Response Cycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                       │
│                  "What is my revenue?"                                   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    [1] MIDDLEWARE: JWT → client_id                       │
│                                                                           │
│  get_access_token() → JWT { sub: "external-user-123" }                  │
│  external_user_id → client_id lookup                                    │
│  Result: cliente_id = "abc-123-uuid"                                    │
│  ✅ client_id NOT exposed to LLM (server-side injection)               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            [2] CONTEXT SERVICE: Load Client Context & RLS              │
│                                                                           │
│  get_client_context_by_id(cliente_id="abc-123-uuid")                   │
│  ├─ Cache check (Redis)                                                │
│  ├─ _set_rls_context() → set_config('app.current_cliente_id', ...)   │
│  └─ Load VizuClientContext from DB                                    │
│                                                                           │
│  Result: VizuClientContext {                                           │
│    id: "abc-123-uuid",                                                │
│    nome_cliente: "Company XYZ",                                        │
│    tier: "PREMIUM",                                                    │
│    enabled_tools: ["executar_sql_agent", "executar_rag_cliente"],    │
│    ...                                                                  │
│  }                                                                       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│     [3] TOOL ENABLED CHECK: Does client have SQL tool access?          │
│                                                                           │
│  _is_tool_enabled_for_client("executar_sql_agent", vizu_context)     │
│  ✓ "executar_sql_agent" in enabled_tools                             │
│  ✓ Client tier supports this tool                                    │
│  ✅ Proceed                                                            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│         [4] SCHEMA LOADING: Get Production Schema Only                 │
│                                                                           │
│  _get_enriched_schema_context(cliente_id, engine)                      │
│                                                                           │
│  TRY:                                                                    │
│    Query sql_table_config for client-specific schema (if exists)       │
│  FALLBACK:                                                              │
│    SQLDatabase with include_tables = [                                 │
│        "analytics_v2.fact_sales",                                      │
│        "analytics_v2.fact_order_metrics",  ← We want this!            │
│        "analytics_v2.fact_product_metrics",                            │
│        "analytics_v2.dim_customer",                                    │
│        "analytics_v2.dim_supplier",                                    │
│        "analytics_v2.dim_product",                                     │
│        "analytics_v2.dim_time",                                        │
│    ]                                                                    │
│  ❌ Excludes: analytics_silver, analytics_gold_*                      │
│                                                                           │
│  Result: Schema string with table definitions and grain documentation │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           [5] LLM SQL GENERATION: Create SQL from NL Query            │
│                                                                           │
│  Prompt to LLM:                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ "You are a SQL expert for analytics_v2 star schema               │ │
│  │                                                                   │ │
│  │ CLIENT_ID: abc-123-uuid (UUID type)                            │ │
│  │ MANDATORY: WHERE client_id = 'abc-123-uuid'                    │ │
│  │                                                                   │ │
│  │ FACT TABLES:                                                    │ │
│  │ - fact_sales: Line items (grain: order_id, line_sequence)     │ │
│  │ - fact_order_metrics: Customer aggregates (grain: customer_id) │ │
│  │                                                                   │ │
│  │ DIMENSION TABLES:                                               │ │
│  │ - dim_customer, dim_supplier, dim_product, dim_time            │ │
│  │                                                                   │ │
│  │ EXAMPLE:                                                         │ │
│  │ Q: "What is total revenue?"                                     │ │
│  │ A: SELECT SUM(fm.total_revenue)                                │ │
│  │    FROM analytics_v2.fact_order_metrics fm                     │ │
│  │    WHERE fm.client_id = 'abc-123-uuid'                         │ │
│  │                                                                   │ │
│  │ USER QUESTION: What is my revenue?                             │ │
│  │ SQL QUERY:"                                                      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  LLM Response:                                                          │
│  SELECT SUM(fm.total_revenue)                                          │
│  FROM analytics_v2.fact_order_metrics fm                               │
│  WHERE fm.client_id = 'abc-123-uuid'                                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               [6] SQL VALIDATION: Multi-Layer Safety                    │
│                                                                           │
│  generated_sql = """SELECT SUM(fm.total_revenue)                       │
│                     FROM analytics_v2.fact_order_metrics fm             │
│                     WHERE fm.client_id = 'abc-123-uuid'"""             │
│                                                                           │
│  Check 1: Basic SQL Validation                                         │
│  ✓ Starts with SELECT (not INSERT/UPDATE/DELETE)                      │
│  ✓ No forbidden keywords                                              │
│                                                                           │
│  Check 2: Production Schema Validation (NEW!)                         │
│  ✓ Only references analytics_v2 (not analytics_silver)                │
│  ✓ Does not use legacy analytics_gold_* tables                        │
│  ✓ Includes WHERE clause with client_id filter                       │
│                                                                           │
│  Result: ✅ All checks passed, ready for execution                    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             [7] RLS CONTEXT: Set PostgreSQL Session Variable          │
│                                                                           │
│  with engine.connect() as conn:                                        │
│    conn.execute(                                                        │
│        "SELECT set_config('app.current_cliente_id', 'abc-123-uuid')"  │
│    )                                                                     │
│    conn.commit()  ← Ensures RLS context is set                        │
│                                                                           │
│  This variable is checked by RLS policies:                            │
│    WHERE client_id = current_setting('app.current_cliente_id')::text │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                [8] SQL EXECUTION: Run the Query                        │
│                                                                           │
│  cursor = conn.execute(sa_text("""SELECT SUM(fm.total_revenue)        │
│                                   FROM analytics_v2.fact_order_metrics │
│                                   WHERE client_id = 'abc-123-uuid'""") │
│  results = cursor.fetchall()                                           │
│                                                                           │
│  Database Processing:                                                   │
│  ├─ Connect to analytics_v2.fact_order_metrics table                  │
│  ├─ Filter: WHERE client_id = 'abc-123-uuid'                         │
│  ├─ Aggregate: SUM(total_revenue)                                     │
│  └─ Return: Row with total_revenue value                              │
│                                                                           │
│  Results: [(50000.00,)]  ← Actual revenue data!                       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    [9] RESULT FORMATTING & RETURN                      │
│                                                                           │
│  {                                                                       │
│    "output": "[{'total_revenue': 50000.00}]",                         │
│    "sql": "SELECT SUM(fm.total_revenue) ...",                         │
│    "success": true                                                      │
│  }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Client ID Injection (Server-Side, Not Exposed to LLM)

```
┌──────────────────────────────────────────────────────────────────┐
│                       AUTHENTICATION                             │
│                                                                   │
│  JWT Token {                                                     │
│    sub: "external-user-123",  ← From Supabase Auth             │
│    iat: 1704067200,                                             │
│    exp: 1704153600,                                             │
│    ...                                                           │
│  }                                                               │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│            MIDDLEWARE: mcp_inject_cliente_id                     │
│                                                                   │
│  @mcp_inject_cliente_id(get_context_service)                    │
│  async def _executar_sql_agent_logic(                           │
│      query: str,                                                │
│      ctx: Context,                                              │
│      cliente_id: str | None = None,  ← Injected HERE           │
│  ):                                                              │
│                                                                   │
│  Middleware logic:                                              │
│  1. Extract JWT sub claim: external_user_id = "external-user-123"
│  2. Lookup: client_id = ContextService.lookup(external_user_id) │
│  3. Inject: kwargs["cliente_id"] = "abc-123-uuid"              │
│                                                                   │
│  ✅ client_id is NEVER passed to LLM, NEVER in prompt text    │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              TOOL FUNCTION (LLM Sees Only Prompt)                │
│                                                                   │
│  async def _executar_sql_agent_logic(                           │
│      query: str,           ← From user: "What is my revenue?"  │
│      ctx: Context,                                              │
│      cliente_id: str = None,  ← From middleware, internal arg   │
│  ):                                                              │
│      # cliente_id is known SERVER-SIDE                         │
│      real_client_id = cliente_id  # "abc-123-uuid"             │
│                                                                   │
│      # LLM prompt includes client_id STRING (not variable)    │
│      prompt = f"""                                             │
│          CLIENT_ID: {real_client_id}  ← Baked into prompt text│
│          ...                                                    │
│          user question: {query}  ← Only this from user         │
│      """                                                         │
│                                                                   │
│      # LLM generates SQL, client_id filter already in prompt   │
│      generated_sql = llm.invoke(prompt)                        │
│      # Result: "SELECT ... WHERE client_id = 'abc-123-uuid'"  │
│                                                                   │
│      ✅ LLM can't change client_id (baked into prompt)        │
│      ✅ LLM can't remove filter (instructed as MANDATORY)     │
│      ✅ LLM can't add other clients (doesn't know about them) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Schema Offered to LLM - Before vs After

### BEFORE (WRONG)
```
Schema presented to LLM:
┌─────────────────────────────┐
│  analytics_silver           │  ← EMPTY, deprecated
│  ├─ client_id               │
│  ├─ order_id                │
│  ├─ data_transacao          │
│  ├─ emitter_nome            │
│  └─ receiver_nome           │
│                             │
│  analytics_gold_customers   │  ← Legacy precomputed
│  ├─ client_id               │
│  ├─ customer_name           │
│  └─ total_orders            │
│                             │
│  analytics_gold_orders      │  ← Legacy precomputed
│  ├─ client_id               │
│  ├─ order_id                │
│  └─ total_revenue           │
│                             │
│  fact_order_metrics         │  ← Production (mixed in)
│  ├─ client_id               │
│  ├─ total_orders            │
│  └─ total_revenue           │
│                             │
│  [30+ other mixed tables]   │
└─────────────────────────────┘

Result when LLM asks "What is my revenue?":
- Ambiguous which table to use
- Might pick analytics_silver (WRONG - no data)
- Might pick analytics_gold_orders (WRONG - legacy)
- Sometimes picks fact_order_metrics (RIGHT)
- User gets inconsistent results
```

### AFTER (CORRECT)
```
Schema presented to LLM:
┌────────────────────────────────────────┐
│  ANALYTICS V2 STAR SCHEMA              │
│                                         │
│  FACT TABLES (Use for aggregates):     │
│  ┌──────────────────────────────────┐ │
│  │ fact_order_metrics (MAIN)        │ │
│  │ ├─ Grain: customer_id per period │ │
│  │ ├─ client_id (UUID)              │ │
│  │ ├─ total_orders (Integer)        │ │
│  │ ├─ total_revenue (Decimal)       │ │
│  │ ├─ avg_order_value               │ │
│  │ ├─ frequencia_pedidos_mes        │ │
│  │ └─ recencia_dias                 │ │
│  │                                   │ │
│  │ fact_sales (Transactional)       │ │
│  │ ├─ Grain: order_id, line_seq    │ │
│  │ ├─ client_id (UUID)              │ │
│  │ ├─ order_id, line_item_sequence  │ │
│  │ ├─ quantity, unit_price          │ │
│  │ └─ line_total                    │ │
│  │                                   │ │
│  │ fact_product_metrics             │ │
│  │ ├─ client_id, product_name       │ │
│  │ ├─ total_quantity_sold           │ │
│  │ └─ total_revenue                 │ │
│  └──────────────────────────────────┘ │
│                                         │
│  DIMENSION TABLES (Use for enrichment): │
│  ┌──────────────────────────────────┐ │
│  │ dim_customer                     │ │
│  │ ├─ client_id, customer_cpf_cnpj  │ │
│  │ ├─ customer_name                 │ │
│  │ └─ tier                          │ │
│  │                                   │ │
│  │ dim_supplier                     │ │
│  │ ├─ client_id, supplier_cnpj      │ │
│  │ └─ supplier_name                 │ │
│  │                                   │ │
│  │ dim_product                      │ │
│  │ ├─ client_id, product_name       │ │
│  │ └─ category                      │ │
│  │                                   │ │
│  │ dim_time                         │ │
│  │ └─ period_date, period_type      │ │
│  └──────────────────────────────────┘ │
│                                         │
│  EXAMPLES:                              │
│  Q: "What is my revenue?"              │
│  A: SELECT SUM(fm.total_revenue)       │
│     FROM analytics_v2.fact_order_...   │
│     WHERE client_id = '...'            │
└────────────────────────────────────────┘

Result when LLM asks "What is my revenue?":
- Clear which table to use (fact_order_metrics)
- Clear join patterns to dimensions
- Clear client_id filtering requirement
- Consistent, correct results every time
```

---

## 4. Data Isolation - RLS + Manual Filtering

```
CLIENT A: client_id = "aaa-111"
CLIENT B: client_id = "bbb-222"

REQUEST FROM CLIENT A:
┌──────────────────────────────────────────┐
│  SQL: SELECT * FROM fact_order_metrics   │
│       WHERE client_id = 'aaa-111'        │
│                                           │
│  Database RLS checks:                    │
│  ├─ current_setting('app.current_cliente_id') = 'aaa-111'
│  ├─ WHERE clause: client_id = 'aaa-111' ✓ MATCH
│  └─ Return: Only rows with client_id = 'aaa-111'
│                                           │
│  Results: [                               │
│      {client_id: 'aaa-111', revenue: ...},
│      {client_id: 'aaa-111', revenue: ...},
│  ]                                        │
└──────────────────────────────────────────┘

REQUEST FROM CLIENT B:
┌──────────────────────────────────────────┐
│  SQL: SELECT * FROM fact_order_metrics   │
│       WHERE client_id = 'aaa-111'        │ ← Same query!
│                                           │
│  Database RLS checks:                    │
│  ├─ current_setting('app.current_cliente_id') = 'bbb-222'
│  ├─ WHERE clause: client_id = 'aaa-111' ✗ NO MATCH
│  └─ Return: EMPTY (RLS blocks Client A's data)
│                                           │
│  Results: []  ← Empty, data properly isolated
└──────────────────────────────────────────┘

SAFETY LAYERS:
1. ✅ Manual filtering: WHERE client_id in generated SQL
2. ✅ LLM instruction: MANDATORY client_id filter
3. ✅ Validation: Check SQL contains client_id before execution
4. ✅ RLS context: Set app.current_cliente_id for PostgreSQL policies
5. ✅ Middleware: client_id never exposed to LLM
6. ✅ Schema: Only relevant tables in schema context
```

---

## 5. Problem-Solution Mapping

```
PROBLEM 1: LLM Querying Wrong Tables
┌─────────────────────────┐
│ LLM sees all tables:     │
│ - analytics_silver       │
│ - analytics_gold_*       │
│ - fact_order_metrics     │
│ - [30+ others]          │
│                          │
│ LLM picks: analytics_silver (WRONG - empty)
│ Result: No data returned
└─────────────────────────┘
              │
              │ SOLUTION
              ▼
┌──────────────────────────┐
│ Filter schema to v2 only:│
│ - fact_sales             │
│ - fact_order_metrics     │
│ - dim_customer           │
│ - dim_supplier           │
│ - dim_product            │
│ - dim_time              │
│                          │
│ LLM picks: fact_order_metrics (RIGHT)
│ Result: Correct data
└──────────────────────────┘

PROBLEM 2: Ambiguous LLM Prompt
┌────────────────────────────┐
│ Prompt says:                │
│ "You have these tables..."  │
│ [schema dump, no context]   │
│                             │
│ LLM confused:               │
│ - Which table for revenue?  │
│ - How to join dimensions?   │
│ - Grain/cardinality unknown│
└────────────────────────────┘
              │
              │ SOLUTION
              ▼
┌────────────────────────────────────┐
│ Prompt says:                        │
│ "fact_order_metrics: Customer-level│
│  aggregates (grain: customer_id)   │
│  Use for revenue, frequency        │
│                                     │
│  Example:                           │
│  SELECT SUM(total_revenue)          │
│  FROM analytics_v2.fact_order_metrics
│  WHERE client_id = '...'           │
│                                     │
│ LLM knows exactly what to do        │
└────────────────────────────────────┘

PROBLEM 3: No Safety Check on Generated SQL
┌──────────────────────────┐
│ LLM outputs:             │
│ "SELECT * FROM          │
│  analytics_silver WHERE  │
│  client_id = 'xxx'"      │
│                          │
│ No validation            │
│ Execute directly         │
│ Result: NOTHING (empty)  │
└──────────────────────────┘
              │
              │ SOLUTION
              ▼
┌──────────────────────────────────┐
│ Validate before execution:        │
│ 1. Must start with SELECT         │
│ 2. Must contain analytics_v2      │
│ 3. Must NOT contain analytics_*  │
│ 4. Must include client_id filter  │
│                                    │
│ If invalid: Return error          │
│ If valid: Execute                │
│ Result: Only safe queries run     │
└──────────────────────────────────┘
```

---

## 6. The "User Sees Data, SQL Sees None" Problem - EXPLAINED

```
USER'S DASHBOARD:
┌────────────────────────────────────────┐
│  Revenue Query:                        │
│  SELECT SUM(total_revenue)             │
│  FROM analytics_v2.fact_order_metrics │
│  WHERE client_id = 'user-id'          │
│  AND period >= '2024-01-01'          │
│                                        │
│  Result: Revenue = $50,000             │
│  ✅ Data found                         │
└────────────────────────────────────────┘

SQL TOOL (OLD):
┌────────────────────────────────────────┐
│  Generated Query:                      │
│  SELECT * FROM analytics_silver        │
│  WHERE client_id = 'user-id'          │
│                                        │
│  analytics_silver = EMPTY TABLE        │
│  Result: No data                       │
│  ❌ Nothing returned                   │
└────────────────────────────────────────┘

SQL TOOL (NEW):
┌────────────────────────────────────────┐
│  Generated Query:                      │
│  SELECT SUM(fm.total_revenue)         │
│  FROM analytics_v2.fact_order_metrics │
│  WHERE fm.client_id = 'user-id'      │
│                                        │
│  Same table as dashboard!              │
│  Result: Revenue = $50,000             │
│  ✅ Data found                         │
└────────────────────────────────────────┘

WHY THE DISCREPANCY?
- Dashboard built by engineers: queries analytics_v2 directly ✅
- SQL Tool built by LLM: queries what it could find in schema
  - Old: Could find analytics_silver → WRONG
  - New: Only sees analytics_v2 → RIGHT
```

