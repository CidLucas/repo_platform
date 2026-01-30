# Debug Logging Summary

## Changes Made

Added **DEBUG level logging** to inspect full LLM prompts across the system. These logs are **deactivated by default** and can be enabled with `LOG_LEVEL=DEBUG`.

---

## Implemented Debug Logs

### 1. Supervisor Node (Main Agent)
**File:** `services/atendente_core/src/atendente_core/core/nodes.py`

**Logs:**
- Full system prompt with Context 2.0 sections
- Complete message list (conversation history)

**Sample output:**
```
[DEBUG] === SUPERVISOR FULL SYSTEM PROMPT ===
Você é um assistente da Vizu.
## EMPRESA
...company profile...
## TOM DE VOZ
...brand voice...
[DEBUG] === END SUPERVISOR SYSTEM PROMPT ===

[DEBUG] === SUPERVISOR FULL MESSAGE LIST (5 messages) ===
Message 0 [SystemMessage]: Você é um assistente da Vizu...
Message 1 [HumanMessage]: Quanto vendemos esse mês?...
[DEBUG] === END SUPERVISOR MESSAGE LIST ===
```

### 2. SQL Tool
**File:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py`

**Logs:**
- Context guidance from Context 2.0
- Schema information (table configs + live introspection)
- User question

**Sample output:**
```
[DEBUG] === SQL GENERATION FULL PROMPT ===
Context guidance:
{"data_schema": {...}, "sql_tool": {...}}

Table info:
analytics_v2.fact_sales
- order_id, data_transacao, customer_id, ...

User question: Quanto vendemos esse mês?
[DEBUG] === END SQL GENERATION PROMPT ===
```

### 3. RAG Tool
**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`

**Logs:**
- Number of documents retrieved
- Full formatted context from Qdrant

**Sample output:**
```
[DEBUG] === RAG RETRIEVED CONTEXT (4 docs) ===
Product A costs $100 and is available...
---
Product B costs $200 and requires...
[DEBUG] === END RAG CONTEXT ===
```

---

## How to Enable Debug Logging

### Temporary (until container restart)
```bash
# Set env var in running container
docker exec -it atendente_core sh -c 'export LOG_LEVEL=DEBUG'
docker exec -it tool_pool_api sh -c 'export LOG_LEVEL=DEBUG'
```

### Permanent (docker-compose.yml)
```yaml
# docker-compose.yml
atendente_core:
  environment:
    - LOG_LEVEL=DEBUG  # ← Add this

tool_pool_api:
  environment:
    - LOG_LEVEL=DEBUG  # ← Add this
```

Then restart:
```bash
make down && make up
```

### View Debug Logs
```bash
# All services:
make logs

# Specific service:
make logs s=atendente_core

# Filter for debug markers:
make logs s=atendente_core | grep "==="

# Real-time with grep:
docker logs -f atendente_core | grep "==="
```

---

## Security Clarification: JWT is NOT Exposed to LLM

**Your concern was valid!** Here's what actually happens:

### JWT Storage (for tool execution only)
```python
# services/atendente_core/src/atendente_core/core/service.py
initial_state = AgentState(
    user_jwt=user_jwt,  # ← Stored for MCP auth, NOT for LLM
    safe_context=safe_ctx,  # ← THIS goes to LLM
    _internal_context=internal_ctx,  # ← Sensitive data, NOT for LLM
)
```

### Context Transformation (safe filtering)
```python
# services/atendente_core/src/atendente_core/core/nodes.py
async def build_dynamic_system_prompt(..., vizu_context: VizuClientContext):
    # Convert to safe context (strips sensitive data)
    llm_safe_context = vizu_context.to_safe_context()

    # Only safe context is compiled for LLM
    context_sections_text = llm_safe_context.get_compiled_context(...)
```

### What LLM Sees vs. Doesn't See

| Data | Exposed to LLM? | Used For |
|------|----------------|----------|
| `user_jwt` | ❌ NO | MCP tool authentication |
| `client_id` (UUID) | ❌ NO | Internal routing, RLS |
| `external_user_id` | ❌ NO | JWT `sub` claim lookup |
| `company_profile` | ✅ YES | Business context |
| `brand_voice` | ✅ YES | Communication style |
| `product_catalog` | ✅ YES | Product knowledge |
| `policies` | ✅ YES | Rules and compliance |
| Database credentials | ❌ NO | Backend operations |
| API keys | ❌ NO | External service calls |

**Implementation:** `libs/vizu_models/src/vizu_models/safe_client_context.py`

---

## Example Debug Session

1. **Enable debug logging:**
   ```bash
   # Edit docker-compose.yml:
   atendente_core:
     environment:
       - LOG_LEVEL=DEBUG

   make down && make up
   ```

2. **Send a message from frontend:**
   ```typescript
   // User asks: "Quanto vendemos em janeiro?"
   ```

3. **Watch logs:**
   ```bash
   make logs s=atendente_core | grep "==="
   ```

4. **See outputs:**
   ```
   [DEBUG] === SUPERVISOR FULL SYSTEM PROMPT ===
   Você é um assistente da ClienteX.
   ## EMPRESA
   Nome: ClienteX
   Setor: Varejo
   ...
   === END ===

   [INFO] LLM escolheu chamar tools: ['executar_sql_agent']

   [DEBUG] === SQL GENERATION FULL PROMPT ===
   Context guidance:
   ...schema mappings...
   User question: Quanto vendemos em janeiro?
   === END ===

   [INFO] SQL executed: SELECT SUM(valor_total) FROM analytics_v2.fact_sales...
   ```

5. **Analyze prompt:**
   - ✅ Company name present
   - ✅ Context 2.0 sections compiled
   - ❌ No JWT visible
   - ❌ No UUIDs visible
   - ✅ Only safe business context

---

## Deactivating Debug Logs (Production)

Default behavior (`LOG_LEVEL=INFO` or not set):
- ✅ INFO logs: Tool calls, execution status, errors
- ❌ DEBUG logs: Full prompts, message lists, context dumps

To ensure debug logs are off:
```yaml
# docker-compose.yml
atendente_core:
  environment:
    - LOG_LEVEL=INFO  # Explicit
```

Or remove `LOG_LEVEL` entirely (defaults to INFO).

---

## Performance Impact

**Debug logging impact:**
- Token: None (no extra API calls)
- Memory: Minimal (string formatting only when log level matches)
- Disk: High (full prompts can be 10-100KB per request)

**Recommendation:**
- Development: `LOG_LEVEL=DEBUG` ✅
- Staging: `LOG_LEVEL=INFO` (default) ✅
- Production: `LOG_LEVEL=WARNING` ⚠️ (only errors/warnings)

---

## Related Documentation

- [PROMPT_CONTEXT_MAPPING.md](PROMPT_CONTEXT_MAPPING.md) - Complete context flow mapping
- Context 2.0 implementation: `libs/vizu_models/src/vizu_models/vizu_client_context.py`
- SafeClientContext filtering: `libs/vizu_models/src/vizu_models/safe_client_context.py`
- Dynamic prompt builder: `services/atendente_core/src/atendente_core/core/nodes.py`
