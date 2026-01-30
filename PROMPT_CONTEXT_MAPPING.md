# Vizu Prompt & Context Flow Mapping

## Overview

This document maps **all sources of context** that feed into LLM prompts across the Vizu workflow, and explains how to inspect/edit each component.

---

## Analytics API "Loading" Operations (Your Log Question)

### What are these logs?

```
analytics_api | ✓ Loaded 2987 customers from analytics_v2.dim_customer
analytics_api | ✓ Loaded 549 suppliers from analytics_v2.dim_supplier
analytics_api | ✓ Loaded 6670 products from analytics_v2.dim_product (period=all)
```

### What's happening?

**Location:** `services/analytics_api/src/analytics_api/data_access/postgres_repository.py`

**Operation:** In-memory data loading for API response enrichment

**Flow:**
1. **Reads from:** PostgreSQL star schema tables (`analytics_v2.dim_*`)
2. **Processes:** Calculates derived metrics (cluster scores, tiers)
3. **Writes to:** In-memory Python lists (returns as JSON via FastAPI)
4. **NO database writes** - this is a READ-ONLY operation

**Code locations:**
- `get_dim_customers()` (lines 1175-1223) → Loads customers with RFM scores
- `get_dim_suppliers()` (lines 1225-1300) → Loads supplier metrics
- `get_dim_products()` (lines 1302-1380) → Loads product metrics

**What gets "loaded":**
```python
# Example from get_dim_customers:
result = self.db_session.execute(query, {"client_id": client_id})
rows = result.fetchall()  # ← This is what "loading" means (DB → RAM)
customers = []
for row in rows:
    customer = dict(zip(columns, row))
    customer['cluster_score'] = (score_r + score_f + score_m) / 3  # Enrichment
    customers.append(customer)
return customers  # ← Returned to FastAPI endpoint as JSON
```

**To inspect/edit:**
- **Query logic:** Edit SQL in `postgres_repository.py` functions
- **Enrichment logic:** Edit the Python calculation code after `fetchall()`
- **Source tables:** Managed by Alembic migrations in `services/analytics_api/migrations/`

---

## Main Prompt Flow Mapping

### Architecture

```
User Message
    ↓
[1] JWT Authentication → external_user_id
    ↓
[2] Context Service → VizuClientContext (Redis cached)
    ↓
[3] Agent Graph (LangGraph) → Supervisor Node
    ↓
[4] Dynamic System Prompt Builder → Context 2.0 Sections
    ↓
[5] Tool Selection → MCP Server (Tool Pool API)
    ↓
[6] Tool Execution → RAG/SQL Factories
    ↓
[7] LLM Response → vizu_llm_service
```

---

## [1] Authentication Context

### Source: JWT Token (from vizu_dashboard)

**⚠️ IMPORTANT: JWT is NOT exposed to the LLM**

The JWT is used for:
1. **Authentication** - Identify which client is making the request
2. **Tool execution** - Propagate auth to MCP tools (stored in `AgentState.user_jwt`)
3. **Database access** - RLS context setting

**The JWT is NEVER included in LLM prompts. Only `SafeClientContext` (without sensitive data) is exposed.**

**Flow:**
```typescript
// Frontend (apps/vizu_dashboard/src/services/supabase.ts)
const { data: session } = await supabase.auth.getSession();
const jwt = session.access_token; // ← Contains user ID
```

**JWT Claims:**
```json
{
  "sub": "uuid-of-supabase-auth-user",  ← Used as external_user_id
  "role": "authenticated",
  "email": "user@client.com"
}
```

**Backend Processing:**
```python
# services/atendente_core/src/atendente_core/api/router.py
# Extracts external_user_id from JWT 'sub' claim
client_context = await context_service.get_client_context_by_external_user_id(
    external_user_id=jwt_payload["sub"]
)

# JWT stored in state for tool execution only (NOT exposed to LLM)
initial_state = AgentState(
    user_jwt=user_jwt,  # ← For MCP auth, not for LLM
    safe_context=safe_ctx,  # ← THIS goes to LLM (no JWT)
    _internal_context=internal_ctx,  # ← Sensitive data (NOT for LLM)
)
```

**To inspect:**
- Frontend: Check `localStorage.getItem('supabase.auth.token')`
- Backend: Add logging in `atendente_core/api/router.py` auth middleware

**To edit:**
- Change auth provider: Edit `libs/vizu_auth/src/vizu_auth/dependencies.py`
- Modify JWT validation: Edit JWT verification logic in `vizu_auth`

---

## [2] Client Context (Context 2.0)

### Source: Supabase `clientes_vizu` table

**Database Schema:**
```sql
-- Table: public.clientes_vizu
CREATE TABLE public.clientes_vizu (
    client_id UUID PRIMARY KEY,
    external_user_id UUID REFERENCES auth.users(id),  -- JWT sub
    nome_empresa TEXT,
    tier TEXT,  -- BASIC/SME/ENTERPRISE

    -- Context 2.0 Modular Sections (ALL JSONB)
    company_profile JSONB,      -- Business description, mission, values
    brand_voice JSONB,           -- Communication style, tone guidelines
    product_catalog JSONB,       -- Products/services offered
    target_audience JSONB,       -- Customer demographics, ICP
    market_context JSONB,        -- Industry trends, competitors
    current_moment JSONB,        -- Active campaigns, seasonal context
    team_structure JSONB,        -- Org chart, escalation paths
    policies JSONB,              -- Rules, compliance, dos/don'ts
    data_schema JSONB,           -- Custom field mappings
    available_tools JSONB,       -- Tool-specific guidance
    client_custom JSONB,         -- Client-specific overrides

    -- Legacy fields
    prompt_base TEXT,
    enabled_tools TEXT[],
    collection_rag TEXT,
    horario_funcionamento JSONB
);
```

**Data Flow:**
```python
# libs/vizu_context_service/src/vizu_context_service/context_service.py

async def get_client_context_by_external_user_id(external_user_id: str):
    # Step 1: Look up cliente by external_user_id (from JWT)
    cliente_data = await supabase_crud.get_cliente_vizu_by_external_user_id(external_user_id)

    # Step 2: Fetch full context (includes RLS setup + Redis caching)
    return await get_client_context_by_id(cliente_data["client_id"])

async def get_client_context_by_id(cliente_id: UUID):
    # Step 1: Check Redis cache (TTL: 5 minutes)
    cached = cache.get_json(f"context:client:{cliente_id}")
    if cached:
        return VizuClientContext.model_validate(cached)

    # Step 2: Fetch from Supabase
    cliente_data = supabase_crud.get_cliente_vizu_by_id(cliente_id)

    # Step 3: Build VizuClientContext (Pydantic model)
    context = VizuClientContext(
        id=cliente_data["client_id"],
        nome_empresa=cliente_data["nome_empresa"],
        tier=cliente_data["tier"],
        company_profile=cliente_data["company_profile"],  # JSONB → dict
        brand_voice=cliente_data["brand_voice"],
        # ... all Context 2.0 sections ...
    )

    # Step 4: Cache for 5 minutes
    cache.set_json(f"context:client:{cliente_id}", context, ttl=300)
    return context
```

**To inspect context for a client:**
```sql
-- In Supabase SQL Editor:
SELECT
    client_id,
    nome_empresa,
    tier,
    company_profile,
    brand_voice,
    product_catalog,
    available_tools
FROM clientes_vizu
WHERE client_id = 'your-uuid-here';
```

**To edit context:**

1. **Via Supabase Dashboard:**
   - Go to Table Editor → `clientes_vizu`
   - Find your client row
   - Edit JSONB fields directly

2. **Via SQL:**
   ```sql
   UPDATE clientes_vizu
   SET brand_voice = jsonb_set(
       brand_voice,
       '{tone}',
       '"professional and empathetic"'
   )
   WHERE client_id = 'your-uuid';
   ```

3. **Via Python Script:**
   ```python
   from vizu_supabase_client import get_supabase_client

   client = get_supabase_client()
   client.table("clientes_vizu").update({
       "company_profile": {
           "industry": "retail",
           "size": "50-100 employees"
       }
   }).eq("client_id", "your-uuid").execute()
   ```

4. **Clear Redis cache after edit:**
   ```bash
   docker exec -it redis-container redis-cli DEL "context:client:your-uuid"
   ```

---

## [3] Dynamic System Prompt Construction

### Source: Custom supervisor node

**Location:** `services/atendente_core/src/atendente_core/core/graph.py`

**Prompt Builder Function:**
```python
def build_dynamic_system_prompt(state: AgentState) -> str:
    """
    Constructs system prompt from Context 2.0 modular sections.

    Context Sections (all optional JSONB):
    - company_profile: Who is the company?
    - brand_voice: How should AI communicate?
    - product_catalog: What do we sell?
    - target_audience: Who are our customers?
    - market_context: Industry/competitive landscape
    - current_moment: Active campaigns, seasonal context
    - team_structure: Escalation paths
    - policies: Rules, compliance requirements
    - data_schema: Custom data field definitions
    - available_tools: Tool-specific guidance
    - client_custom: Client-specific overrides
    """

    ctx = state.vizu_context
    parts = []

    # Base role
    parts.append("Você é um assistente da Vizu.")

    # Company Profile
    if ctx.company_profile:
        parts.append(f"\n## EMPRESA\n{json.dumps(ctx.company_profile, indent=2)}")

    # Brand Voice
    if ctx.brand_voice:
        parts.append(f"\n## TOM DE VOZ\n{json.dumps(ctx.brand_voice, indent=2)}")

    # Product Catalog
    if ctx.product_catalog:
        parts.append(f"\n## PRODUTOS\n{json.dumps(ctx.product_catalog, indent=2)}")

    # ... continues for all sections ...

    return "\n".join(parts)
```

**Full Prompt Structure:**
```
[SYSTEM MESSAGE - Built from Context 2.0]
Você é um assistente da Vizu.

## EMPRESA
{company_profile JSONB}  ← From SafeClientContext (no sensitive data)

## TOM DE VOZ
{brand_voice JSONB}

## PRODUTOS
{product_catalog JSONB}

## PÚBLICO-ALVO
{target_audience JSONB}

## CONTEXTO DE MERCADO
{market_context JSONB}

## MOMENTO ATUAL
{current_moment JSONB}

## ESTRUTURA DE TIME
{team_structure JSONB}

## POLÍTICAS
{policies JSONB}

## FERRAMENTAS DISPONÍVEIS
{available_tools JSONB}

[USER MESSAGE]
{user_input}

[ASSISTANT RESPONSE]
```

**Security Note:**
All context passed to LLM comes from `SafeClientContext` via `vizu_context.to_safe_context()`, which:
- ✅ Includes: Business context, policies, tools, brand voice
- ❌ Excludes: JWT tokens, API keys, database credentials, internal IDs
- ❌ Excludes: `_internal_context` fields (client_id, external_user_id)

See `libs/vizu_models/src/vizu_models/safe_client_context.py` for implementation.

**To inspect full prompt:**
Debug logging is already implemented (see "Complete Prompt Inspection Checklist" section below). Enable with `LOG_LEVEL=DEBUG`.

**To edit prompt structure:**
- **Base template:** Edit `build_dynamic_system_prompt()` in `nodes.py`
- **Section content:** Edit JSONB in `clientes_vizu` table (see [2])
- **Section ordering:** Change order in `build_dynamic_system_prompt()` parts list

---

## [4] Versioned Prompt Templates (Phase 5)

### Source: Supabase `prompt_template` table

**Schema:**
```sql
CREATE TABLE public.prompt_template (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clientes_vizu(client_id),  -- NULL = global
    name TEXT,              -- e.g., "supervisor_system_prompt"
    version INT,            -- Incremental version number
    template_text TEXT,     -- Actual prompt template
    is_active BOOLEAN,      -- Only active versions are used
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**Usage:**
```python
# services/tool_pool_api/src/tool_pool_api/server/resources.py

def _get_prompt_template(name: str, cliente_id: str | None, version: int | None):
    # Step 1: Try client-specific prompt
    if cliente_id:
        query = select(PromptTemplate).where(
            PromptTemplate.name == name,
            PromptTemplate.client_id == uuid_obj,
            PromptTemplate.is_active == True
        )
        if version:
            query = query.where(PromptTemplate.version == version)
        else:
            query = query.order_by(PromptTemplate.version.desc())  # Latest

        result = db.execute(query).first()
        if result:
            return result

    # Step 2: Fallback to global prompt
    query = select(PromptTemplate).where(
        PromptTemplate.name == name,
        PromptTemplate.client_id == None,  # Global
        PromptTemplate.is_active == True
    )
    # ... same version logic ...
```

**To inspect templates:**
```sql
-- All active prompts for a client:
SELECT name, version, LEFT(template_text, 100) as preview
FROM prompt_template
WHERE client_id = 'your-uuid' AND is_active = true;

-- Global templates:
SELECT name, version, LEFT(template_text, 100) as preview
FROM prompt_template
WHERE client_id IS NULL AND is_active = true;
```

**To create new version:**
```sql
-- Insert new version (automatically becomes active if is_active = true)
INSERT INTO prompt_template (
    id, client_id, name, version, template_text, is_active
) VALUES (
    gen_random_uuid(),
    'your-client-uuid',  -- or NULL for global
    'sql_system_prompt',
    2,  -- Increment version
    'Your new prompt text here',
    true
);

-- Deactivate old version:
UPDATE prompt_template
SET is_active = false
WHERE name = 'sql_system_prompt' AND version = 1;
```

---

## [5] Tool-Specific Prompts

### A. SQL Tool Prompt

**Location:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py`

**Prompt Construction:**
```python
async def _executar_sql_agent_logic(query: str, cliente_id: str):
    # Step 1: Get client context
    vizu_context = await ctx_service.get_client_context_by_id(cliente_id)

    # Step 2: Get schema metadata (Redis-cached)
    table_info = await _get_enriched_schema_context(cliente_id, engine)

    # Step 3: Build context-specific guidance
    context_guidance = _build_context_guidance(vizu_context)

    # Step 4: Construct SQL generation prompt
    sql_generation_prompt = f"""You are a SQL expert. Generate the SIMPLEST query.

{context_guidance}  ← From Context 2.0 data_schema + available_tools

=== SCHEMA ===
analytics_v2.fact_sales (source of truth for revenue/quantity)
- order_id, data_transacao, customer_id, supplier_id, product_id
- quantidade, valor_unitario, valor_total

analytics_v2.dim_customer (RELIABLE geography data)
- customer_id, name, cpf_cnpj
- endereco_cidade, endereco_uf

{table_info}  ← From sql_table_config + live schema introspection

=== RULES ===
1. NEVER include client_id in SELECT - it's HARD-INJECTED after generation
2. Use fact_sales for all revenue/quantity queries
3. Use dim_customer geography fields (not dim_supplier)
4. Keep queries simple - avoid subqueries unless necessary

=== USER QUESTION ===
{query}

=== SQL OUTPUT (plain SQL only, no markdown) ===
"""

    # Step 5: Generate SQL with LLM
    llm_response = await llm.ainvoke([HumanMessage(content=sql_generation_prompt)])
    raw_sql = llm_response.content.strip()

    # Step 6: Validate and inject client_id filter (CRITICAL SECURITY)
    validated_sql = validate_and_inject_client_filter(raw_sql, cliente_id)

    # Step 7: Execute SQL
    result = engine.execute(text(validated_sql))
    return result.fetchall()
```

**Context Sources:**

1. **Schema Context (`table_info`):**
   ```python
   # Source: sql_table_config table (per-client custom metadata)
   async def _get_enriched_schema_context(cliente_id: UUID, engine):
       # Step 1: Get custom table configs (Redis-cached)
       configs = await ctx_service.get_sql_table_configs(cliente_id)

       # Step 2: Introspect live schema
       inspector = inspect(engine)
       tables = inspector.get_table_names(schema='analytics_v2')

       # Step 3: Merge custom + live metadata
       enriched = []
       for table in tables:
           custom = next((c for c in configs if c['table_name'] == table), None)
           columns = inspector.get_columns(table, schema='analytics_v2')

           enriched.append({
               'table': table,
               'columns': columns,
               'description': custom.get('description') if custom else None,
               'sample_queries': custom.get('sample_queries') if custom else []
           })

       return format_schema_for_llm(enriched)
   ```

2. **Context Guidance (`context_guidance`):**
   ```python
   def _build_context_guidance(vizu_context: VizuClientContext) -> str:
       parts = []

       # From Context 2.0 data_schema section
       if vizu_context.data_schema:
           parts.append("## DATA SCHEMA NOTES")
           parts.append(json.dumps(vizu_context.data_schema, indent=2))

       # From Context 2.0 available_tools section (tool-specific guidance)
       if vizu_context.available_tools:
           sql_guidance = vizu_context.available_tools.get('sql_tool', {})
           if sql_guidance:
               parts.append("## SQL TOOL GUIDANCE")
               parts.append(json.dumps(sql_guidance, indent=2))

       return "\n\n".join(parts)
   ```

**To inspect SQL prompt:**
```python
# Add logging in sql_module.py:
logger.info(f"=== SQL GENERATION PROMPT ===\n{sql_generation_prompt}\n=== END ===")
```

**To edit SQL prompt:**

1. **Base template:** Edit `sql_generation_prompt` string in `sql_module.py`
2. **Schema descriptions:** Edit `sql_table_config` table per client
3. **Custom rules:** Edit `data_schema` JSONB in `clientes_vizu`
4. **Tool guidance:** Edit `available_tools.sql_tool` JSONB in `clientes_vizu`

### B. RAG Tool Prompt

**Location:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`

**Prompt Template:**
```python
RAG_PROMPT_TEMPLATE = """
Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.
O contexto é soberano. Se você não sabe a resposta com base no contexto,
apenas diga que não sabe. Não tente inventar uma resposta.

CONTEXTO:
{context}  ← Retrieved from Qdrant vector store

---

PERGUNTA:
{question}

RESPOSTA:
"""
```

**Data Flow:**
```python
# services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py

async def _executar_rag_cliente_logic(query: str, cliente_id: str):
    # Step 1: Get client context
    vizu_context = await ctx_service.get_client_context_by_id(cliente_id)

    # Step 2: Create RAG runnable (uses collection_rag from context)
    rag_runnable = create_rag_runnable(vizu_context, llm)

    # Step 3: Execute RAG chain
    # Inside create_rag_runnable:
    #   - Retrieves docs from Qdrant (collection = vizu_context.collection_rag)
    #   - Formats docs into context string
    #   - Injects into RAG_PROMPT_TEMPLATE
    #   - Sends to LLM
    result = await rag_runnable.ainvoke({"question": query})
    return result
```

**Context Sources:**

1. **Vector Store (Qdrant):**
   ```python
   # Collection name from clientes_vizu.collection_rag
   collection_name = vizu_context.collection_rag  # e.g., "cliente-abc-123"

   # Retrieval
   retriever = qdrant_client.get_langchain_retriever(
       collection_name=collection_name,
       embeddings=get_embedding_model(),
       search_k=4  # Top 4 documents
   )
   docs = retriever.invoke(query)
   ```

2. **Retrieved Documents Format:**
   ```python
   # Each doc has:
   doc.page_content = "Your knowledge base text chunk..."
   doc.metadata = {"source": "document_name.pdf", "page": 5}
   ```

**To inspect RAG prompt:**
```python
# Add to vizu_rag_factory/factory.py:
def retrieve_and_format(input_dict):
    question = input_dict.get("question", "")
    docs = retriever.invoke(question)
    context = _format_docs(docs)

    logger.info(f"=== RAG CONTEXT ===\n{context}\n=== END ===")
    return context
```

**To edit RAG prompt:**

1. **Template:** Edit `RAG_PROMPT_TEMPLATE` in `vizu_rag_factory/factory.py`
2. **Collection content:** Add/update documents in Qdrant (see seed scripts)
3. **Retrieval parameters:** Edit `search_k` in `get_langchain_retriever()` call
4. **Collection name:** Edit `collection_rag` column in `clientes_vizu` table

---

## [6] Tool Registry Context

### Source: `vizu_tool_registry`

**Location:** `libs/vizu_tool_registry/src/vizu_tool_registry/registry.py`

**How it injects context:**
```python
def is_tool_enabled_for_client(tool_name: str, client_context: VizuClientContext) -> bool:
    # Step 1: Check if tool is in client's enabled_tools list
    if tool_name not in client_context.enabled_tools:
        return False

    # Step 2: Check tier access (BASIC/SME/ENTERPRISE)
    tool_tier = TOOL_TIER_MAP.get(tool_name)
    client_tier = client_context.tier

    tier_hierarchy = {"BASIC": 1, "SME": 2, "ENTERPRISE": 3}
    return tier_hierarchy[client_tier] >= tier_hierarchy[tool_tier]
```

**To inspect available tools for client:**
```python
from vizu_tool_registry import get_available_tools
from vizu_context_service import get_context_service

ctx_service = get_context_service()
client_context = await ctx_service.get_client_context_by_id("your-uuid")
available = get_available_tools(client_context)
print(available)  # List of tool names
```

**To edit tool access:**

1. **Enable/disable tool for client:**
   ```sql
   -- Add tool to enabled_tools array:
   UPDATE clientes_vizu
   SET enabled_tools = array_append(enabled_tools, 'executar_sql_agent')
   WHERE client_id = 'your-uuid';

   -- Remove tool:
   UPDATE clientes_vizu
   SET enabled_tools = array_remove(enabled_tools, 'executar_sql_agent')
   WHERE client_id = 'your-uuid';
   ```

2. **Change tier:**
   ```sql
   UPDATE clientes_vizu
   SET tier = 'ENTERPRISE'  -- or 'SME', 'BASIC'
   WHERE client_id = 'your-uuid';
   ```

3. **Add new tool to registry:**
   ```python
   # Edit libs/vizu_tool_registry/src/vizu_tool_registry/registry.py

   TOOL_TIER_MAP = {
       "executar_rag_cliente": "BASIC",
       "executar_sql_agent": "SME",
       "your_new_tool": "ENTERPRISE",  # ← Add here
   }
   ```

---

## [7] LLM Model Selection

### Source: `vizu_llm_service`

**Location:** `libs/vizu_llm_service/src/vizu_llm_service/client.py`

**Model Tier System:**
```python
from vizu_llm_service import get_model, ModelTier

# Three tiers with different models:
llm = get_model(
    tier=ModelTier.FAST,      # Fast/cheap (e.g., gpt-4o-mini)
    tier=ModelTier.DEFAULT,   # Balanced (e.g., gpt-4o)
    tier=ModelTier.POWERFUL,  # Powerful (e.g., o1-pro)

    task="sql_agent",         # Optional task tag for observability
    user_id="client-uuid",    # For usage tracking
    tags=["tool_pool", "sql"] # Custom tags
)
```

**Configuration:**
```python
# Env vars (docker-compose.yml or .env):
OLLAMA_CLOUD_API_KEY=your-openai-key
OLLAMA_CLOUD_DEFAULT_MODEL=gpt-4o
OLLAMA_CLOUD_FAST_MODEL=gpt-4o-mini
OLLAMA_CLOUD_POWERFUL_MODEL=o1-pro
```

**To inspect which model is used:**
```python
# Add logging:
logger.info(f"Using LLM: {llm.model_name} (tier={tier}, task={task})")
```

**To change model for specific client:**
```python
# Per-request override:
result = await atendente_service.process_message(
    session_id="abc",
    message_text="Hello",
    client_id="uuid",
    model_override="gpt-4-turbo"  # ← Override default
)
```

---

## Complete Prompt Inspection Checklist

### Debug Logging (Already Implemented)

To see **full prompts** the LLM sees, set `LOG_LEVEL=DEBUG` in docker-compose.yml:

```yaml
# docker-compose.yml
atendente_core:
  environment:
    - LOG_LEVEL=DEBUG  # ← Enable debug logging

tool_pool_api:
  environment:
    - LOG_LEVEL=DEBUG
```

**Debug logs are already implemented in:**

1. **Supervisor (main agent)** - `services/atendente_core/src/atendente_core/core/nodes.py`
   - Full system prompt
   - Complete message list (conversation history)

2. **SQL tool** - `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py`
   - Context guidance
   - Schema information
   - User question

3. **RAG tool** - `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`
   - Retrieved documents
   - Formatted context

**To activate debug logging:**
```bash
# Temporary (until container restart):
docker exec -it atendente_core sh -c 'export LOG_LEVEL=DEBUG'

# Permanent: Edit docker-compose.yml and restart
make down && make up

# View debug logs:
make logs s=atendente_core | grep "==="
```

### 2. SQL Tool Prompt (Legacy Reference)

**File:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py`

```python
async def _executar_sql_agent_logic(...):
    sql_generation_prompt = f"""You are a SQL expert..."""

    # ADD THIS LINE:
    logger.info(f"=== SQL GENERATION PROMPT ===\n{sql_generation_prompt}\n=== END ===")

    llm_response = await llm.ainvoke([HumanMessage(content=sql_generation_prompt)])
```

### 3. RAG Tool Prompt

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`

```python
def retrieve_and_format(input_dict):
    docs = retriever.invoke(question)
    context = _format_docs(docs)

    # ADD THIS LINE:
    logger.info(f"=== RAG RETRIEVED CONTEXT ===\n{context}\n=== END ===")

    return context
```

### 4. View Logs in Real-Time

```bash
# Tail all services:
make logs

# Specific service:
make logs s=atendente_core
make logs s=tool_pool_api
make logs s=analytics_api

# Or directly:
docker logs -f atendente_core --tail=100
```

---

## Quick Edit Commands

### Edit Context for a Client

```bash
# 1. Get current context:
docker exec -it postgres-container psql -U vizu -d vizu_db -c "
SELECT jsonb_pretty(brand_voice) FROM clientes_vizu WHERE client_id = 'your-uuid';
"

# 2. Update context:
docker exec -it postgres-container psql -U vizu -d vizu_db -c "
UPDATE clientes_vizu
SET brand_voice = '{
  \"tone\": \"professional\",
  \"style\": \"concise\",
  \"emoji_usage\": false
}'::jsonb
WHERE client_id = 'your-uuid';
"

# 3. Clear Redis cache:
docker exec -it redis-container redis-cli DEL "context:client:your-uuid"

# 4. Test immediately - cache is now stale, will fetch fresh data
```

### Edit SQL Table Descriptions

```sql
-- Add/update table description for SQL agent:
INSERT INTO sql_table_config (
    id, client_id, table_name, description, sample_queries
) VALUES (
    gen_random_uuid(),
    'your-uuid',
    'fact_sales',
    'Main transaction table. Use this for ALL revenue and quantity queries.',
    '["SELECT SUM(valor_total) FROM analytics_v2.fact_sales"]'
)
ON CONFLICT (client_id, table_name) DO UPDATE
SET description = EXCLUDED.description;
```

### Edit RAG Collection

```python
# Add documents to Qdrant:
from vizu_qdrant_client import get_qdrant_client
from vizu_llm_service import get_embedding_model

client = get_qdrant_client()
embeddings = get_embedding_model()

# Your documents:
docs = [
    {"text": "Product A costs $100", "metadata": {"source": "catalog.pdf"}},
    {"text": "Product B costs $200", "metadata": {"source": "catalog.pdf"}}
]

# Add to collection:
client.add_documents(
    collection_name="cliente-abc-123",  # From clientes_vizu.collection_rag
    texts=[d["text"] for d in docs],
    metadatas=[d["metadata"] for d in docs],
    embeddings=embeddings
)
```

---

## Summary: Where is Each Piece?

| Context Source | Database Location | Code Location | Edit Method |
|----------------|-------------------|---------------|-------------|
| **Client Identity** | `clientes_vizu.client_id` | JWT auth | Change user in auth.users |
| **Company Profile** | `clientes_vizu.company_profile` (JSONB) | Context 2.0 | SQL UPDATE or Supabase UI |
| **Brand Voice** | `clientes_vizu.brand_voice` (JSONB) | Context 2.0 | SQL UPDATE or Supabase UI |
| **Product Catalog** | `clientes_vizu.product_catalog` (JSONB) | Context 2.0 | SQL UPDATE or Supabase UI |
| **Policies** | `clientes_vizu.policies` (JSONB) | Context 2.0 | SQL UPDATE or Supabase UI |
| **Tool Access** | `clientes_vizu.enabled_tools` (array) | Tool Registry | SQL array manipulation |
| **Tier** | `clientes_vizu.tier` | Tool Registry | SQL UPDATE |
| **System Prompt Template** | `prompt_template` table | Versioned prompts | SQL INSERT (new version) |
| **SQL Schema Descriptions** | `sql_table_config` table | SQL tool | SQL INSERT/UPDATE |
| **RAG Knowledge Base** | Qdrant vector store | RAG tool | Python script with Qdrant client |
| **Dynamic Prompt Logic** | N/A | `atendente_core/core/graph.py` | Edit Python code |
| **SQL Tool Prompt** | N/A | `tool_pool_api/server/tool_modules/sql_module.py` | Edit Python string |
| **RAG Tool Prompt** | N/A | `vizu_rag_factory/factory.py` | Edit Python constant |
| **LLM Model** | Env vars (docker-compose.yml) | `vizu_llm_service` | Edit OLLAMA_CLOUD_*_MODEL |

---

## Context Caching Strategy

### Redis Cache Keys

```
context:client:{uuid}              TTL: 5 minutes
sql_configs:{uuid}                 TTL: 10 minutes
schema_snapshot:{uuid}             TTL: 1 hour
```

### Cache Invalidation

```bash
# Invalidate specific client context:
docker exec -it redis-container redis-cli DEL "context:client:your-uuid"

# Invalidate SQL configs:
docker exec -it redis-container redis-cli DEL "sql_configs:your-uuid"

# Invalidate all caches for a client:
docker exec -it redis-container redis-cli --scan --pattern "*your-uuid*" | xargs docker exec -it redis-container redis-cli DEL
```

---

## Next Steps for Prompt Engineering

1. **Add logging** to see full prompts (use checklist above)
2. **Edit Context 2.0 sections** in `clientes_vizu` table
3. **Test immediately** - changes take effect on next request (after cache expiry)
4. **Version control prompts** - use `prompt_template` table for A/B testing
5. **Monitor performance** - check Langfuse traces for token usage and latency

All prompt changes are **hot-reloadable** - no service restarts needed (after Redis cache expires).
