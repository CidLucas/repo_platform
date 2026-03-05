# Vizu Mono 🚀

**Multi-tenant conversational AI platform** built with Python 3.11+, FastAPI, LangGraph, and Poetry.

Autonomous agents with RAG, SQL analytics, and Model Context Protocol (MCP) tool orchestration.

---

## 🎯 Quick Start

### Local Development (New! 💰 Save on CI/CD costs)

```bash
# 1. Ensure Docker Desktop is running
open -a Docker

# 2. Start core dev stack (dashboard + backend + tools)
make dev

# 3. Open dashboard
open http://localhost:8080
```

**Services:**
- 🎨 Dashboard: http://localhost:8080
- 🤖 Atendente Core: http://localhost:8003
- 🔧 Tool Pool API: http://localhost:8006

**Your code is hot-reloaded!** Edit and save → changes apply instantly.

**Connects to remote Supabase** → No local database maintenance.

📖 **New to local dev?** Read [QUICK_START.md](./QUICK_START.md) for step-by-step setup.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [QUICK_START.md](./QUICK_START.md) | Step-by-step checklist to get running in 5 minutes |
| [DEV_SETUP.md](./DEV_SETUP.md) | Complete local development guide with workflows |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, data flows, and troubleshooting |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Coding standards, library usage, anti-patterns |

---

## 🏗️ Architecture

```
vizu-mono/
├── apps/
│   ├── vizu_dashboard/        # React frontend (Vite + TypeScript)
│   └── hitl_dashboard/        # Human-in-the-loop review UI
├── services/
│   ├── atendente_core/        # Main LangGraph orchestrator (port 8003)
│   ├── tool_pool_api/         # FastMCP server - RAG + SQL tools (port 8006)
│   ├── vendas_agent/          # Sales specialist agent
│   ├── support_agent/         # Support specialist agent
│   ├── file_upload_api/       # Document ingestion
└── libs/                      # 20+ shared Python libraries
    ├── vizu_models/           # ALL database models + API schemas
    ├── vizu_llm_service/      # Provider-agnostic LLM client
    ├── vizu_agent_framework/  # Build agents with 95% code reuse
    ├── vizu_db_connector/     # Database sessions + migrations
    ├── vizu_supabase_client/  # Supabase REST API singleton
    ├── vizu_tool_registry/    # Tool discovery + tier access
    ├── vizu_rag_factory/      # RAG chain construction
    ├── vizu_sql_factory/      # Text-to-SQL agent
    └── ...                    # 12+ more libs
```

**Philosophy:** Shared libraries = ZERO code duplication across services.

---

## 🛠️ Development Commands

### Core Workflow

```bash
make dev              # Start core dev stack (fast!)
make dev-logs         # View logs from dev services
make dev-down         # Stop services
make dev-rebuild      # Rebuild after dependency changes
```

### Full Stack

```bash
make up               # Start ALL services + workers
make down             # Stop all services
make logs             # Tail all logs
make logs s=<name>    # Logs for specific service
make ps               # Show running containers
```

### Testing

```bash
make chat             # Quick chat test via curl
make test             # Run unit tests (atendente_core)
make test-all         # Test all services
make smoke-test       # Comprehensive E2E test
make experiment-run   # Run evaluation experiments
```

### Database

```bash
make seed             # Seed dev data (DB + Qdrant)
make migrate-prod     # Apply migrations to Supabase
make db-shell         # Open psql shell
```

### Code Quality

```bash
make fmt              # Format code (ruff)
make lint             # Lint code (ruff check)
make lint-fix         # Auto-fix lint issues
```

---

## 💡 Key Features

### Agentic AI
- **LangGraph workflows** with conditional routing, parallel tool execution, and state management
- **Multi-provider LLM support**: OpenAI, Anthropic, Google, Ollama, open-source (DeepSeek)
- **Model Context Protocol (MCP)**: Autonomous tool use (RAG, SQL, Google Workspace)

### Multi-Tenant Architecture
- **Row-Level Security (RLS)** with Supabase
- **JWT-based auth** with API key validation
- **Per-client tool access** via tier-based registry (BASIC/SME/ENTERPRISE)

### Observability
- **Langfuse integration**: Full trace lineage, tool calls, confidence scores
- **OpenTelemetry**: Metrics and traces
- **Human-in-the-Loop (HITL)**: Queue low-confidence interactions for review

### Data Pipeline
- **BigQuery → Supabase FDW**: Automated data ingestion
- **RAG**: Semantic search over per-client knowledge bases (Qdrant)
- **Text-to-SQL**: Natural language analytics queries

---

## 🔧 Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, TypeScript, Vite, TanStack Query, Supabase Auth |
| **Backend** | FastAPI, Python 3.11+, Poetry, Pydantic |
| **AI/ML** | LangGraph, LangChain, OpenAI/Anthropic/Ollama, HuggingFace embeddings |
| **Database** | Supabase (PostgreSQL 15), Qdrant (vector DB), Redis (cache) |
| **Tools** | FastMCP (Model Context Protocol), Google APIs, Twilio |
| **Observability** | Langfuse, OpenTelemetry, Grafana Cloud |
| **Infra** | Docker Compose, Google Cloud Run, Artifact Registry |

---

## 🚀 Deployment

### Local Development
```bash
make dev  # Uses remote Supabase
```

### Staging/Production
```bash
# Build for Cloud Run (3-group architecture)
make compose-cloud

# Build and push to Artifact Registry
make cloudrun-push-all

# Deploy via Cloud Build (automated on push)
gcloud builds submit --config cloudbuild.yaml
```

---

## 📊 Data Model (Supabase)

### Core Tables
- `clientes_vizu` - B2B clients (companies using Vizu)
- `cliente_final` - End users of B2B clients
- `conversa` - Chat sessions
- `mensagem` - Individual messages

### Data Pipeline
- `credencial_servico_externo` - BigQuery/API credentials
- `client_data_sources` - Column mappings for ingestion
- `analytics_silver` - Normalized transaction data
- `bigquery_servers` / `bigquery_foreign_tables` - FDW config

### AI/Config
- `prompt_template` - Versioned prompts per client
- `knowledge_base_config` - RAG collection settings
- `sql_table_config` - Text-to-SQL metadata
- `hitl_review` - Human review queue
- `experiment_run` / `experiment_case` - A/B testing

---

## 🎓 Learning Resources

### For Developers
1. Start with [QUICK_START.md](./QUICK_START.md) - get running in 5 minutes
2. Read [ARCHITECTURE.md](./ARCHITECTURE.md) - understand how everything connects
3. Study [.github/copilot-instructions.md](.github/copilot-instructions.md) - coding standards
4. Explore individual service READMEs in `services/` and `libs/`

### For AI Development
- [services/atendente_core/](services/atendente_core/) - LangGraph workflow examples
- [services/tool_pool_api/](services/tool_pool_api/) - MCP tool patterns
- [libs/vizu_agent_framework/](libs/vizu_agent_framework/) - Reusable agent builder
- [ferramentas/evaluation_suite/](ferramentas/evaluation_suite/) - Testing workflows

---

## 🤝 Contributing

### Code Standards (Critical!)

```python
# ✅ CORRECT - Use shared libraries
from vizu_models import ClienteVizu
from vizu_llm_service.client import get_model
from vizu_agent_framework import AgentBuilder

# ❌ WRONG - Never call providers directly
from langchain_openai import ChatOpenAI  # FORBIDDEN

# ✅ CORRECT - Provider-agnostic, Pydantic in/out, bulk operations
async def process_messages(
    messages: list[MessageInput],  # Pydantic
    db: AsyncSession,
) -> list[MessageOutput]:
    await db.execute(insert(Message).values([m.model_dump() for m in messages]))

# ❌ WRONG - Dict in/out, one-by-one writes
def process(msg: dict):
    for m in messages:
        db.add(Message(**m))  # Slow!
```

**Must read:** [.github/copilot-instructions.md](.github/copilot-instructions.md)

### Commit Standards
1. `make lint` must pass
2. Run tests: `make test`
3. Update relevant README if changing public API

### Adding New Tools
See [services/tool_pool_api/src/tool_pool_api/server/tool_modules/](services/tool_pool_api/src/tool_pool_api/server/tool_modules/) for examples.

---

## 💰 Cost Optimization

**Problem:** GitHub Actions → Cloud Build on every commit = $5-20/build

**Solution:** Local dev with `make dev`

| Approach | Cost/Day (10 builds) | Month (20 workdays) |
|----------|---------------------|---------------------|
| CI/CD per commit | $50-200 | $1,000-4,000 |
| **Local dev** | **$0** | **$0** |

**Savings:** ~$12k-48k/year per developer 🎉

---

## 📞 Support

- Report issues via GitHub Issues
- Read [ARCHITECTURE.md](./ARCHITECTURE.md) troubleshooting section
- Check service-specific READMEs for detailed debugging

---

## 📄 License

Proprietary - Vizu © 2025

---

**Built with ❤️ by the Vizu team**
