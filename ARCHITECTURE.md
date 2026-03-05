# Local Development Architecture

## Overview

This document describes how your local development environment connects to remote Supabase while running core services locally.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR LOCAL MACHINE                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🎨 vizu_dashboard (React + Vite)        :8080          │   │
│  │     - Hot reload enabled                                 │   │
│  │     - Volume: ./apps/vizu_dashboard/src                 │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │ HTTP                                         │
│                   ↓                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🤖 atendente_core (FastAPI + LangGraph)  :8003         │   │
│  │     - Main orchestrator                                  │   │
│  │     - Hot reload enabled                                 │   │
│  │     - Volume: ./services/atendente_core/src             │   │
│  │     - Volume: ./libs (shared libraries)                 │   │
│  └────┬──────────────────────┬──────────────────────────────┘   │
│       │                      │ MCP Protocol                     │
│       │                      ↓                                   │
│       │         ┌─────────────────────────────────────────┐     │
│       │         │  🔧 tool_pool_api (FastMCP)     :8006   │     │
│       │         │     - RAG tools (pgvector)               │     │
│       │         │     - SQL agent                          │     │
│       │         │     - Google integrations                │     │
│       │         │     - Hot reload enabled                 │     │
│       │         └────────┬────────────────────────────────┘     │
│       │                  │                                       │
│       │ Redis            │ Supabase Edge Functions               │
│       ↓                  ↓                                       │
│  ┌────────────┐    ┌──────────────┐                            │
│  │ 📦 Redis   │    │ ☁️  Supabase │                            │
│  │   :6379    │    │   pgvector   │                            │
│  │            │    │              │                            │
│  │ Sessions + │    │ Vector DB    │                            │
│  │ Checkpoints│    │ RAG search   │                            │
│  └────────────┘    └──────────────┘                            │
│                                                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Supabase REST API
                       │ (SUPABASE_URL + SUPABASE_SERVICE_KEY)
                       ↓
            ┌──────────────────────────┐
            │   ☁️  Supabase Cloud     │
            │                          │
            │  📊 PostgreSQL Database  │
            │     - clientes_vizu      │
            │     - conversa           │
            │     - mensagem           │
            │     - vector_db schema   │
            │       (pgvector RAG)     │
            │     - analytics_silver   │
            │                          │
            │  🔐 Auth & Row Level     │
            │      Security (RLS)      │
            │                          │
            │  📁 Storage Buckets      │
            └──────────────────────────┘
```

## Service Details

### Frontend: vizu_dashboard (:8080)

**Purpose:** Web UI for interacting with the AI assistant

**Tech Stack:**
- React 18 + TypeScript
- Vite (build tool with HMR)
- TanStack Query for data fetching
- Supabase Auth for authentication

**Hot Reload:**
```yaml
volumes:
  - ./apps/vizu_dashboard/src:/app/src  # Auto-reload on changes
```

**Environment:**
```bash
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_URL=http://localhost:8003
VITE_TOOL_POOL_API_URL=http://localhost:8006
```

---

### Backend: atendente_core (:8003)

**Purpose:** Main LangGraph orchestrator - handles conversation flow

**Tech Stack:**
- FastAPI (REST API)
- LangGraph (agent orchestration)
- LangChain (LLM abstraction)
- vizu_agent_framework (95% code reuse)

**Key Responsibilities:**
- Route messages to appropriate agents
- Manage conversation state (Redis checkpoints)
- Call tools via MCP (tool_pool_api)
- Query Supabase for client context

**Hot Reload:**
```yaml
volumes:
  - ./services/atendente_core/src:/app/services/atendente_core/src
  - ./libs:/app/libs  # All shared libs hot-reload too!
```

**Dependencies:**
```python
from vizu_models import ClienteVizu, Conversa  # Shared models
from vizu_llm_service.client import get_model  # Provider-agnostic LLMs
from vizu_agent_framework import AgentBuilder   # Agent construction
from vizu_supabase_client import get_supabase_client  # DB access
```

---

### Tools: tool_pool_api (:8006)

**Purpose:** MCP server exposing RAG, SQL, and integration tools

**Tech Stack:**
- FastMCP (Model Context Protocol server)
- vizu_rag_factory (semantic search)
- vizu_sql_factory (text-to-SQL)
- vizu_google_suite_client (Calendar/Drive)

**Available Tools:**
- `executar_rag_cliente` - Search knowledge base
- `executar_sql_agent` - Natural language → SQL queries
- `google_calendar_event` - Create calendar events
- `google_drive_upload` - Upload to Drive
- `web_scraper` - Fetch web content

**Hot Reload:**
```yaml
volumes:
  - ./services/tool_pool_api/src:/app/services/tool_pool_api/src
  - ./libs:/app/libs  # Shared libs
```

**Tool Discovery:**
```python
# atendente_core calls tools via MCP
from vizu_mcp_commons.client import MCPClient

async with MCPClient("http://tool_pool_api:8000/mcp/") as client:
    result = await client.call_tool("executar_rag_cliente", {
        "query": "políticas de devolução",
        "cliente_id": "uuid-here"
    })
```

---

### Infrastructure: Redis (:6379)

**Purpose:** Fast in-memory storage

**Uses:**
- LangGraph checkpoints (conversation state)
- Session cache
- Rate limiting counters

**Data Examples:**
```json
// Session cache
{
  "session:abc123": {
    "cliente_id": "uuid",
    "context": {...}
  }
}

// LangGraph checkpoint
{
  "checkpoint:abc123:step5": {
    "state": {...},
    "next": ["tool_call", "human_input"]
  }
}
```

---

### Infrastructure: Qdrant (:6333)

**Purpose:** Vector database for semantic search (RAG)

**Collections:**
- `vizu_knowledge_base` - Company docs per client
- `vizu_conversations` - Past conversation embeddings

**Vector Flow:**
```
User Query
   ↓
Embedding Service (or external API)
   ↓
Vector (384 or 1024 dimensions)
   ↓
Qdrant Search (cosine similarity)
   ↓
Top 5 most relevant docs
   ↓
LLM receives context + query
```

---

### Remote: Supabase (Cloud)

**Purpose:** Primary data store (PostgreSQL + REST API)

**Key Tables:**
- `clientes_vizu` - B2B clients
- `cliente_final` - End users
- `conversa` - Chat sessions
- `mensagem` - Individual messages
- `analytics_silver` - Transaction data (BigQuery sync)

**Access Pattern:**
```python
from vizu_supabase_client.client import get_supabase_client

client = get_supabase_client()
response = client.table("clientes_vizu") \
    .select("*") \
    .eq("client_id", uuid) \
    .single() \
    .execute()
```

**Why Remote?**
- ✅ Same data as staging/prod
- ✅ No local DB maintenance
- ✅ Real-time sync across team
- ✅ RLS policies enforced
- ✅ Backup/restore handled by Supabase

---

## Data Flow Example

### User sends message: "Qual a política de devolução?"

```
1. 🎨 Dashboard (localhost:8080)
   POST /chat
   ↓
2. 🤖 atendente_core (localhost:8003)
   - Loads conversation from Supabase
   - Retrieves client context (tier, tools enabled)
   - Builds LangGraph agent
   ↓
3. 🔧 tool_pool_api (localhost:8006)
   - Agent calls RAG tool via MCP
   - Searches Qdrant for "política de devolução"
   - Returns top 3 knowledge base docs
   ↓
4. 🤖 atendente_core
   - LLM generates response with context
   - Saves message to Supabase
   - Returns response
   ↓
5. 🎨 Dashboard
   - Displays AI response
   - Updates UI
```

**Time:** ~2-3 seconds end-to-end

---

## Development Benefits

### Hot Reload Stack

| Service | Hot Reload | Restart Needed |
|---------|-----------|----------------|
| vizu_dashboard | ✅ Instant (Vite HMR) | ❌ |
| atendente_core | ✅ ~2s (uvicorn --reload) | ❌ |
| tool_pool_api | ✅ ~2s (uvicorn --reload) | ❌ |
| Shared libs (vizu_models, etc.) | ✅ Instant (volume mount) | ❌ |
| pyproject.toml changes | ❌ | ✅ `make dev-rebuild` |

### Cost Comparison

| Approach | Build Time | Cost per Build | Daily Cost (10 builds) |
|----------|-----------|----------------|------------------------|
| **GitHub Actions → Cloud Build** | 8-12 min | $3-8 | $30-80 |
| **Local Dev (`make dev`)** | Build once: 2-3 min<br>Then: instant | $0 | $0 |

**Savings:** ~$600-2,400/month per developer

---

## Troubleshooting

### "Connection refused" to Supabase

```bash
# Check .env
grep SUPABASE_URL .env
grep SUPABASE_SERVICE_KEY .env

# Test connection
curl -X GET "https://xxx.supabase.co/rest/v1/clientes_vizu?select=nome_empresa&limit=1" \
  -H "apikey: YOUR_SERVICE_KEY" \
  -H "Authorization: Bearer YOUR_SERVICE_KEY"
```

### Qdrant Not Starting

```bash
# Check logs
make logs s=qdrant_db

# Verify data volume
docker volume ls | grep qdrant

# Recreate if corrupted
docker compose down -v qdrant_db
make dev
```

### Redis Connection Issues

```bash
# Test connection
docker exec -it vizu_redis_dev redis-cli ping
# Should return: PONG

# Check keys
docker exec -it vizu_redis_dev redis-cli KEYS '*'
```

### Dashboard Can't Reach Backend

```bash
# Verify CORS settings in atendente_core
# services/atendente_core/src/atendente_core/main.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Must match!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Next Steps

- 📖 Read [DEV_SETUP.md](./DEV_SETUP.md) for detailed setup guide
- 🚀 See [QUICK_START.md](./QUICK_START.md) for step-by-step checklist
- 🧪 Check [Makefile](./Makefile) for all available commands
- 📝 Review [.github/copilot-instructions.md](.github/copilot-instructions.md) for coding standards
