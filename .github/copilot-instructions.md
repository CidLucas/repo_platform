# Vizu Mono — AI Coding Agent Instructions

**Monorepo for conversational AI platform** built with Python 3.11+, FastAPI, LangGraph, and Poetry.

## Architecture Overview

```
vizu-mono/
├── libs/           # 20+ shared Python libraries (code reuse is CRITICAL)
├── services/       # 14 microservices (FastAPI + Docker)
├── apps/           # React frontends (vizu_dashboard, hitl_dashboard)
└── ferramentas/    # Development tools
```

**Core Services:**
- `atendente_core` (port 8003) — Main LangGraph orchestrator, connects to tool_pool_api via MCP
- `tool_pool_api` (port 8006) — FastMCP server exposing RAG and SQL tools
- `embedding_service` (port 11435) — HuggingFace embeddings

---

## Shared Libraries — CRITICAL (Never Duplicate Code)

| Library | Purpose | Key Pattern |
|---------|---------|-------------|
| `vizu_models` | ALL database models + API schemas (SQLModel/Pydantic) | `from vizu_models import ClienteVizu, Conversa` |
| `vizu_llm_service` | ALL LLM calls — provider-agnostic | `get_model(tier="FAST\|DEFAULT\|POWERFUL")` |
| `vizu_agent_framework` | Build new agents with 95% code reuse | `AgentBuilder(AgentConfig(...)).build()` |
| `vizu_db_connector` | Database sessions + Alembic migrations | `Depends(get_db_session)` |
| `vizu_supabase_client` | Supabase REST API (singleton) | `get_supabase_client().table("x").select("*")` |
| `vizu_tool_registry` | Tool discovery + tier access (BASIC/SME/ENTERPRISE) | `ToolRegistry.get_available_tools(tier="SME")` |
| `vizu_auth` | JWT + API-Key auth | `Depends(verify_api_key)` |
| `vizu_rag_factory` | RAG chain construction | Semantic search over Qdrant |
| `vizu_sql_factory` | Text-to-SQL agent | Natural language → SQL queries |
| `vizu_context_service` | Client context retrieval + Redis caching | `get_client_context_by_id(uuid)` |
| `vizu_elicitation_service` | Human-in-the-loop interactive prompts | `raise ElicitationRequired(...)` |
| `vizu_hitl_service` | Quality control queue for human review | Low confidence → HITL queue |
| `vizu_observability_bootstrap` | OpenTelemetry + Langfuse setup | `setup_observability(app)` |

**Usage Rules:**
```python
# ✅ CORRECT
from vizu_models import ClienteVizu
from vizu_llm_service.client import get_model
from vizu_agent_framework import AgentConfig, AgentBuilder

# ❌ WRONG — never call providers directly
from langchain_openai import ChatOpenAI  # FORBIDDEN
```

---

## Tool Pool API — Adding New Tools

All AI tools live in `tool_pool_api`. Structure: `services/tool_pool_api/src/tool_pool_api/server/tool_modules/`

**Existing modules:**
- `rag_module.py` — `executar_rag_cliente` (knowledge base search)
- `sql_module.py` — `executar_sql_agent` (text-to-SQL)
- `common_module.py` — Test/utility tools
- `google_module.py` — Google Calendar/Drive integration
- `web_monitor_module.py` — Web scraping tools

**Adding a new tool:**
```python
# tool_modules/my_module.py
from fastmcp import Context, FastMCP
from . import register_module

async def _my_tool_logic(query: str, ctx: Context, cliente_id: str | None = None) -> str:
    """Business logic — testable without MCP."""
    # Always validate client has access via vizu_tool_registry
    return result

@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    @mcp.tool(name="my_new_tool")
    async def my_new_tool(query: str, ctx: Context) -> str:
        """Docstring becomes tool description for LLM."""
        return await _my_tool_logic(query, ctx)
    return ["my_new_tool"]
```

**Then register in `__init__.py`:**
```python
from . import common_module, rag_module, sql_module, my_module  # Add import
```

---

## Supabase Database Schema (Primary Tables)

All data lives in Supabase PostgreSQL. RLS enabled on all tables.

**Core tables:**
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `clientes_vizu` | B2B clients (companies using Vizu) | `client_id` (UUID PK), `nome_empresa`, `tier`, `enabled_tools[]`, `collection_rag` |
| `cliente_final` | End-users of B2B clients | `id`, `cliente_vizu_id` (FK), `nome`, `id_externo` |
| `conversa` | Chat sessions | `id` (UUID), `session_id`, `cliente_final_id` |
| `mensagem` | Individual messages | `conversa_id` (FK), `remetente` (user/ai), `conteudo` |

**Data pipeline tables:**
| Table | Purpose |
|-------|---------|
| `credencial_servico_externo` | BigQuery/API credentials per client |
| `client_data_sources` | Column mappings for data ingestion |
| `connector_sync_history` | Sync job tracking |
| `analytics_silver` | Normalized transaction data (silver layer) |
| `bigquery_servers` / `bigquery_foreign_tables` | FDW configuration |

**AI/Config tables:**
| Table | Purpose |
|-------|---------|
| `prompt_template` | Versioned prompts per client |
| `knowledge_base_config` | RAG collection settings |
| `sql_table_config` | Text-to-SQL table metadata |
| `hitl_review` | Human review queue |
| `experiment_run` / `experiment_case` | A/B testing results |

**Access pattern:** Always use `vizu_supabase_client` singleton:
```python
from vizu_supabase_client.client import get_supabase_client
client = get_supabase_client()
response = client.table("clientes_vizu").select("*").eq("client_id", uuid).execute()
```

---

## Data Ingestion Pipeline (BigQuery FDW)

Client data flows from BigQuery → Supabase via Foreign Data Wrapper:

```
BigQuery (client's data)
    ↓
credencial_servico_externo  ← Encrypted credentials per client
    ↓
bigquery_servers            ← FDW server config (project_id, dataset_id, vault_key)
    ↓
bigquery_foreign_tables     ← Table mappings (columns JSONB)
    ↓
client_data_sources         ← Column mapping (source → canonical schema)
    ↓
analytics_silver            ← Normalized data (silver layer)
    ↓
connector_sync_history      ← Job tracking (status, records_processed, errors)
```

**Key tables:**
- `credencial_servico_externo` — Stores encrypted BigQuery service account JSON per `client_id`
- `client_data_sources` — Maps source columns to canonical schema (`column_mapping` JSONB)
- `connector_sync_history` — Tracks sync jobs with `status` (running/completed/failed), progress, errors

**Sync job flow:**
1. Create credential → `credencial_servico_externo`
2. Discover schema → populate `source_columns` in `client_data_sources`
3. Map columns → `column_mapping` (auto or manual)
4. Run sync → insert job in `connector_sync_history`, update `analytics_silver`

---

## Code Standards — MANDATORY

### Function Design
```python
# ✅ Provider-agnostic, Pydantic in/out, bulk-aware
async def process_messages(
    messages: list[MessageInput],  # Pydantic model
    db: AsyncSession,
) -> list[MessageOutput]:  # Pydantic model
    # Bulk insert for performance
    await db.execute(insert(Message).values([m.model_dump() for m in messages]))

# ❌ Bad: hardcoded provider, dict in/out, one-by-one writes
def process_message(message: dict, provider="openai"):
    for m in messages:
        db.add(Message(**m))  # Slow!
```

### Naming Conventions
```python
# Tables: snake_case plural (clientes_vizu, mensagem)
# Models: PascalCase singular (ClienteVizu, Mensagem)
# Functions: snake_case verb_noun (get_client_context, execute_rag_search)
# Constants: UPPER_SNAKE (MAX_RETRIES, DEFAULT_TIER)
# Private: _leading_underscore (_internal_helper)
```

### Type Hints (Python 3.11+)
```python
# ✅ Modern syntax
def get_client(id: str, cache: bool = True) -> ClienteVizu | None:

# ❌ Old syntax
from typing import Optional
def get_client(id: str) -> Optional[ClienteVizu]:  # FORBIDDEN
```

### Performance Patterns
```python
# ✅ Parallel external calls
import asyncio
results = await asyncio.gather(
    fetch_from_api_a(query),
    fetch_from_api_b(query),
)

# ✅ Bulk database operations
await db.execute(insert(Model).values(records))  # Single statement

# ❌ Sequential calls, one-by-one writes
for item in items:
    await fetch_from_api(item)  # Slow!
    db.add(Model(**item))       # Slow!
```

---

## Poetry — ALWAYS Use

```bash
cd services/<service>
poetry add new-package      # Add dependency
poetry lock                 # CRITICAL — always lock after changes
poetry install              # Install from lock file
poetry run pytest           # Run commands in venv
```

**Path dependencies for monorepo:**
```toml
[tool.poetry.dependencies]
vizu-models = {path = "../../libs/vizu_models", develop = true}
```

---

## Development Commands

```bash
make up              # Start all services (docker compose)
make logs s=<name>   # Tail logs for specific service
make down            # Stop all services
make lint            # ruff check (must pass before commit)
make fmt             # ruff format
make migrate         # Apply Alembic migrations
make seed            # Seed dev database + Qdrant
```

---

## What NOT to Do

- ❌ Create inline Pydantic models — use `vizu_models`
- ❌ Call LLM providers directly — use `vizu_llm_service`
- ❌ Write custom LangGraph from scratch — use `vizu_agent_framework`
- ❌ Hardcode tool lists — use `vizu_tool_registry`
- ❌ Skip `poetry lock` after dependency changes
- ❌ Commit code failing `ruff check`
- ❌ Use `dict` for function inputs/outputs — use Pydantic models
- ❌ Write one-by-one DB inserts — use bulk operations
- ❌ Make sequential API calls — use `asyncio.gather()`

---

## Reference Files

- [services/tool_pool_api/src/tool_pool_api/server/tool_modules/](services/tool_pool_api/src/tool_pool_api/server/tool_modules/) — Tool implementation examples
- [services/atendente_core/Dockerfile](services/atendente_core/Dockerfile) — Canonical Docker pattern
- [services/vendas_agent/](services/vendas_agent/) — Example agent using vizu_agent_framework
- [docker-compose.yml](docker-compose.yml) — Service ports and environment setup

## Detailed Guide

For comprehensive documentation (1900+ lines), see [.github/claude-code-guide.md](.github/claude-code-guide.md).
