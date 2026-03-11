# Vizu Mono

**Multi-tenant Data Platform for AI agents** — Python 3.11+, FastAPI, LangGraph, Supabase, React 18.

Autonomous agents with hybrid RAG, text-to-SQL analytics, human-in-the-loop quality control, and Model Context Protocol (MCP) tool orchestration.

---

## Quick Start

```bash
# 1. Ensure Docker Desktop is running
open -a Docker

# 2. Start core dev stack (dashboard + backend + tools)
make dev

# 3. Open dashboard
open http://localhost:8080
```

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:8080 | React SPA (Vite + hot reload) |
| Atendente Core | http://localhost:8003 | LangGraph agent orchestrator |
| Tool Pool API | http://localhost:8006 | FastMCP tool server |

All services support **hot reload** — edit and save, changes apply instantly.
Connects to **remote Supabase** — no local database to maintain.

> New to the project? See [QUICK_START.md](./QUICK_START.md) for a step-by-step setup checklist.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [QUICK_START.md](./QUICK_START.md) | Get running in 5 minutes |
| [DEV_SETUP.md](./DEV_SETUP.md) | Complete local development guide with workflows |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, data flows, troubleshooting |
| [docs/HYBRID_RETRIEVER_AS_BUILT.md](./docs/HYBRID_RETRIEVER_AS_BUILT.md) | RAG pipeline as-built reference |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Coding standards, library usage, anti-patterns |

---

## Architecture

```
vizu-mono/
├── apps/
│   ├── vizu_dashboard/          # React 18 + TypeScript + Chakra UI + Supabase Auth
│   └── hitl_dashboard/          # Streamlit — human review queue UI
├── services/
│   ├── atendente_core/          # LangGraph orchestrator (port 8003)
│   ├── tool_pool_api/           # FastMCP server — RAG, SQL, Google, web tools (port 8006)
│   ├── vendas_agent/            # Sales specialist (AgentBuilder)
│   ├── support_agent/           # Support specialist (AgentBuilder)
│   └── file_upload_api/         # Document ingestion + GCS upload
├── libs/                        # 20+ shared Python libraries (zero duplication)
│   ├── vizu_agent_framework/    # Build agents with 95% code reuse
│   ├── vizu_llm_service/        # Provider-agnostic LLM — 4 providers × 3 tiers
│   ├── vizu_models/             # ALL SQLModel/Pydantic schemas — single source of truth
│   ├── vizu_rag_factory/        # Hybrid retrieval + Cohere reranking + MMR diversity
│   ├── vizu_sql_factory/        # Text-to-SQL with RLS, allowlists, PII masking
│   ├── vizu_tool_registry/      # Tier-based tool access (FREE → ADMIN, 6 levels)
│   ├── vizu_context_service/    # Client context + Redis caching + credential encryption
│   ├── vizu_prompt_management/  # Langfuse-first prompts + Jinja2 fallback + circuit breaker
│   ├── vizu_hitl_service/       # 8-criteria quality evaluation + Redis priority queue
│   ├── vizu_elicitation_service/# Human-in-the-loop interactive prompts
│   ├── vizu_mcp_commons/        # MCP auth, context injection, parallel tool execution
│   ├── vizu_observability_bootstrap/ # One-call OpenTelemetry + Langfuse + Grafana setup
│   ├── vizu_auth/               # Multi-algorithm JWT + Google Secret Manager
│   ├── vizu_data_connectors/    # BigQuery, Shopify, VTEX, Loja Integrada connectors
│   ├── vizu_experiment_service/ # YAML manifest experiments + confidence classification
│   └── ...                      # db_connector, supabase_client, parsers, twilio, shared_utils
└── supabase/
    ├── migrations/              # Versioned schema migrations
    └── functions/               # Deno edge functions (embed, search, process, enrich)
```

### Design Principle: Shared Libraries, Zero Duplication

Every cross-cutting concern lives in a dedicated `libs/` package. Services import, never reimplement. Adding a new agent requires only an `AgentConfig` and `AgentBuilder` call — the framework provides the graph, checkpointing, MCP connection, and observability.

---

## Scalability Architecture

### Multi-Tenancy via Row-Level Security

Tenant isolation is enforced at the **database layer**, not the application layer:

- **PostgreSQL RLS** — Every query sets `app.current_cliente_id` on the connection before execution. Rows outside the tenant scope are invisible regardless of application logic.
- **SQL Factory RLS wrapper** — `RLSContextDatabase` wraps LangChain's `SQLDatabase` to inject tenant context into every text-to-SQL query.
- **Supabase Edge Functions** — `process-document` and `search-documents` filter by `cliente_id` in all queries.
- **MCP context injection** — `@inject_cliente_context` decorator resolves JWT → `external_user_id` → `VizuClientContext` and injects it as a kwarg into every tool call.

### Tier-Based Access Control (6 Levels)

```
FREE → BASIC → SME → PREMIUM → ENTERPRISE → ADMIN
```

| Tier | Tools | Rate Limit |
|------|-------|------------|
| FREE | Basic queries | 10/day, 1 session |
| BASIC | RAG search | 100/day |
| SME | + SQL analytics + scheduling | 1,000/day |
| PREMIUM | + Google Workspace integrations | 5,000/day |
| ENTERPRISE | + Docker MCP (GitHub, Slack, Stripe, Jira, Notion) | Unlimited |
| ADMIN | Full access | Unlimited |

Tier enforcement happens at multiple layers: `ToolRegistry` catalog, `@require_tier` decorators in MCP, and SQL `AllowlistConfig` with per-role column/table restrictions.

### Provider-Agnostic LLM Service

```python
from vizu_llm_service.client import get_model

model = get_model(tier="FAST")      # gpt-4o-mini / claude-3-5-haiku / gemini-flash
model = get_model(tier="DEFAULT")   # gpt-4o-mini / claude-3-5-sonnet / gemini-flash
model = get_model(tier="POWERFUL")  # gpt-4o / claude-3-5-sonnet / gemini-pro
```

4 providers (OpenAI, Anthropic, Google, Ollama/DeepSeek) × 3 tiers = 12 model configs. Switch providers via `LLM_PROVIDER` env var — zero code changes. Token budget management prevents context window overflow with progressive message truncation.

### Hybrid RAG Pipeline

Semantic search powered by **Supabase pgvector** + **Cohere**:

| Stage | Component | Details |
|-------|-----------|---------|
| Embedding | `embed-multilingual-light-v3.0` | 384-dim vectors, Supabase Edge Function |
| Retrieval | Hybrid (semantic + keyword) | RRF or weighted fusion, theme filtering |
| Reranking | `rerank-multilingual-v3.0` | CohereReranker (default), cross-encoder and LLM options |
| Diversity | MMR Diversifier | Lambda-tunable redundancy reduction |
| Preprocessing | Query Preprocessor | Language detection, expansion, intent classification |

Per-client configuration via `knowledge_base_config` table — each client can tune `score_threshold`, `top_k`, `chunk_size`, `reranker_type`, and fusion weights.

### Redis Caching Strategy

| Cache | TTL | Key Pattern | Purpose |
|-------|-----|-------------|---------|
| Client context | 5 min | `context:client:{id}` | Avoid repeated DB lookups |
| LangGraph checkpoints | 24 h | `vizu:checkpoint:{thread_id}` | Multi-turn conversation state |
| Elicitation state | 1 h | `vizu:elicitation:{session_id}` | Pending human-in-the-loop prompts |
| Tool results | 1 h | `tool:{session}:{name}:{args_hash}` | Deduplicate expensive tool calls |
| HITL queue | Configurable | Redis sorted sets | Priority-ordered review queue |

### Horizontal Service Separation

Each service is an independent FastAPI container with its own Dockerfile, health checks, and Cloud Run deployment:

```
atendente_core  ──MCP──►  tool_pool_api
       │                       │
       ▼                       ▼
  LangGraph Agent        RAG / SQL / Google / Web tools
       │
   ┌───┴───┐
   ▼       ▼
vendas   support
agent    agent
```

Services communicate via **Model Context Protocol (MCP)** over Streamable HTTP — the agent orchestrator calls tool servers through a standardized protocol, enabling independent scaling and deployment.

---

## Engineering Practices

### Agent Framework — 95% Code Reuse

New agents are declared, not built from scratch:

```python
from vizu_agent_framework import AgentBuilder, AgentConfig

config = AgentConfig(
    name="vendas_agent",
    system_prompt="You are a sales specialist...",
    tools=["rag_search", "sql_query", "schedule_meeting"],
    mcp_server_url="http://tool_pool_api:8006/mcp",
)

agent = (
    AgentBuilder(config)
    .with_llm(tier="DEFAULT")
    .with_mcp()
    .with_checkpointer()       # Redis-backed state persistence
    .with_langfuse()           # Automatic trace instrumentation
    .use_default_graph()       # init → elicit → execute_tool → respond → end
    .build()
)
```

Custom behavior is injected via `@NodeRegistry.register("name")` decorators — the framework handles the graph topology, MCP connections, checkpointing, and observability.

### Human-in-the-Loop Quality Control

Two complementary systems ensure response quality:

**HITL Service** — 8 configurable criteria route interactions for human review:
- `LOW_CONFIDENCE` — LLM confidence below threshold (default 0.7)
- `KEYWORD_TRIGGER` — Pattern matching for sensitive terms
- `TOOL_CALL_FAILED` — Automatic routing on tool errors
- `FIRST_N_MESSAGES` — Review first N messages per session
- `RANDOM_SAMPLE` — Statistical sampling at configurable rate
- `SENTIMENT_NEGATIVE` — Regex-based negative sentiment detection
- `MANUAL_FLAG` — Explicit human flagging
- `ELICITATION_PENDING` — Active human-in-the-loop prompts

Reviews flow to a **Redis priority queue** (sorted sets + pipeline transactions) and are displayed in the Streamlit **HITL Dashboard**. Approved reviews automatically feed into **Langfuse datasets** for continuous evaluation and fine-tuning.

**Elicitation Service** — Exception-driven control flow (`raise ElicitationRequired(...)`) pauses the agent graph to collect user input (confirmations, selections, text, datetime), then resumes execution.

### Prompt Management with Circuit Breaker

```python
from vizu_prompt_management import build_prompt

prompt = build_prompt(
    name="agent_system_prompt",
    variables={"client_name": "Acme Corp", "tools": available_tools},
    label="production",     # Langfuse version label
)
```

- **Langfuse-first**: Fetches versioned prompts from Langfuse (2s timeout)
- **Circuit breaker**: After a failure, skips Langfuse for 60s and uses Jinja2 fallback templates
- **Label-based versioning**: `production` / `staging` / `latest` enables A/B testing of prompts
- **Trace linking**: Every prompt carries its name, version, and source for Langfuse correlation

### Text-to-SQL with Multi-Layer Security

The SQL Factory transforms natural language into safe, tenant-isolated queries:

1. **RLS context** — Sets `app.current_cliente_id` before every query
2. **Allowlist validation** — Per-tenant, per-role allowed tables, columns, aggregates, and join paths
3. **DDL/DML blocking** — Rejects `CREATE`, `DROP`, `INSERT`, `UPDATE`, `DELETE`
4. **LIMIT enforcement** — Adds configurable row limits to prevent full table scans
5. **PII masking** — `ResultSanitizer` redacts email, phone, credit card, and SSN patterns
6. **Schema snapshots** — LLM receives a role-filtered view of the schema, not the full database

Connection pooling: singleton engine with `pool_size=5`, `max_overflow=10`, `pool_recycle=180s`, `pool_pre_ping=True`.

### Observability Stack

One-call setup wires the full observability pipeline:

```python
from vizu_observability_bootstrap import setup_observability

setup_observability(app, "atendente-core")
```

| Signal | Pipeline | Destination |
|--------|----------|-------------|
| Traces | OpenTelemetry OTLP (HTTP/gRPC) | Grafana Tempo |
| Logs | Structured JSON with trace/span IDs | Grafana Loki |
| Metrics | OTLP Metrics | Grafana Mimir |
| LLM Traces | Langfuse SDK (sanitized) | Langfuse |
| Frontend | Grafana Faro | Grafana Cloud |

- `SanitizingLangfuseCallback` — Truncates messages, removes internal context, trims `response_metadata` to prevent trace bloat
- `GrafanaLokiFormatter` — JSON logs with embedded OTel trace context for cross-signal correlation
- Health endpoints (`/health`, `/ready`, `/live`, `/metrics`) — Kubernetes and Cloud Run compatible

### Experiment-Driven Development

```bash
make experiment-run          # Run YAML manifest experiments
make experiment-workflow     # LangGraph workflow experiments
```

YAML manifests define test cases. `ExperimentRunner` executes them with `asyncio.Semaphore` rate limiting (5 parallel). `ResponseClassifier` routes results through confidence thresholds — high confidence auto-approves, low confidence routes to HITL review. Results feed back into Langfuse datasets.

### Data Connectors (Plugin Architecture)

```python
from vizu_data_connectors import ConnectorFactory

connector = ConnectorFactory.create_connector("BIGQUERY", credentials)
schema = await connector.fetch_schema()
data = await connector.extract_data(query)
```

Abstract base class `AbstractDataConnector` defines the contract. Implementations: BigQuery, PostgreSQL, MySQL, Shopify, VTEX, Loja Integrada. All use encrypted credentials from Google Secret Manager.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, TypeScript 5.9, Vite 5, Chakra UI v2, TanStack Query, Supabase Auth, Recharts, Leaflet, Grafana Faro |
| **Backend** | FastAPI, Python 3.11+, Poetry, Pydantic, SQLModel |
| **AI/ML** | LangGraph, LangChain, OpenAI, Anthropic, Google, Ollama/DeepSeek |
| **RAG** | Supabase pgvector (384d), Cohere embed + rerank, hybrid retrieval, MMR diversity |
| **Database** | Supabase (PostgreSQL + pgvector + RLS + Edge Functions), Redis |
| **Tools** | FastMCP (Model Context Protocol), Docker MCP Bridge, Google APIs, Twilio |
| **Observability** | Langfuse v3, OpenTelemetry, Grafana Cloud (Tempo + Loki + Mimir + Faro) |
| **Infra** | Docker Compose, Google Cloud Run, Artifact Registry, Google Secret Manager |
| **Quality** | Ruff (lint + format), HITL review queue, experiment service, Langfuse datasets |

---

## Development Commands

### Core Workflow

```bash
make dev              # Start dashboard + backend + tools (hot reload)
make dev-logs         # Tail dev service logs
make dev-down         # Stop dev stack
make dev-rebuild      # Rebuild after dependency changes
```

### Full Stack

```bash
make up               # Start ALL services + workers
make down             # Stop all services
make logs s=<name>    # Logs for specific service
make ps               # Show running containers
```

### Testing & Experiments

```bash
make chat             # Quick chat test via curl
make test             # Unit tests (atendente_core)
make test-all         # Test all services
make smoke-test       # End-to-end integration test
make test-agents      # Agent-specific tests
make experiment-run   # YAML manifest experiments
```

### Database

```bash
make migrate          # Run local Alembic migrations
make migrate-prod     # Apply to Supabase (interactive confirmation)
make migrate-status   # Check migration state
make db-shell         # Open psql shell
make seed             # Seed development data
```

### Code Quality

```bash
make fmt              # Format code (ruff format)
make lint             # Lint code (ruff check)
make lint-fix         # Auto-fix lint issues
```

### Deployment

```bash
make compose-cloud       # Local Cloud Run testing
make cloudrun-build      # Build all service images
make cloudrun-push-all   # Push to Artifact Registry
```

---

## Deployment

### Local Development
```bash
make dev  # Remote Supabase, local services with hot reload
```

### Cloud Run (Production)

Each service builds to a standalone Docker image and deploys independently to Google Cloud Run:

```
${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/vizu-mono/<service>:${IMAGE_TAG}
```

- **Profile-based Docker Compose** — `local` profile for Postgres + migrator, `observability` profile for self-hosted Langfuse + ClickHouse + MinIO
- **YAML anchors** — `x-common-env` and `x-atendente-env` for DRY environment configuration
- **Health checks** on every service for orchestrator-managed restarts
- **Production migrations** require interactive confirmation (`make migrate-prod`)

---

## Data Model (Supabase)

### Core Tables
| Table | Description |
|-------|-------------|
| `clientes_vizu` | B2B clients (companies using Vizu) |
| `cliente_final` | End users of B2B clients |
| `conversa` | Chat sessions with metadata |
| `mensagem` | Individual messages |

### Data Pipeline
| Table | Description |
|-------|-------------|
| `credencial_servico_externo` | Encrypted BigQuery/API credentials |
| `client_data_sources` | Column mappings for ingestion |
| `analytics_silver` | Normalized transaction data |
| `bigquery_servers` / `bigquery_foreign_tables` | FDW configuration |

### AI & Configuration
| Table | Description |
|-------|-------------|
| `knowledge_base_config` | Per-client RAG settings (score_threshold, top_k, reranker_type, fusion weights) |
| `sql_table_config` | Text-to-SQL metadata and allowlists |
| `prompt_template` | Versioned prompts per client |
| `hitl_review` | Human review queue entries |
| `experiment_run` / `experiment_case` | A/B testing and evaluation |

### Vector Storage (`vector_db` schema)
| Table | Description |
|-------|-------------|
| `documents` | Chunked documents with 384-dim pgvector embeddings |
| `document_metadata_queue` | pgmq queue for async metadata enrichment |

---

## Contributing

### Code Standards

```python
# Always use shared libraries — never call providers directly
from vizu_models import ClienteVizu
from vizu_llm_service.client import get_model
from vizu_agent_framework import AgentBuilder

# Provider-agnostic, Pydantic in/out, async, bulk operations
async def process_messages(
    messages: list[MessageInput],
    db: AsyncSession,
) -> list[MessageOutput]:
    await db.execute(insert(Message).values([m.model_dump() for m in messages]))
```

**Required reading:** [.github/copilot-instructions.md](.github/copilot-instructions.md)

### Commit Checklist
1. `make lint` passes
2. `make test` passes
3. Update relevant docs if changing public API

### Adding New Tools

Tool modules live in [services/tool_pool_api/src/tool_pool_api/server/tool_modules/](services/tool_pool_api/src/tool_pool_api/server/tool_modules/). Each module registers its tools with the MCP server. Add a new module file, register it in the server config, and update the `ToolRegistry` catalog with tier permissions.

### Adding New Agents

```python
# 1. Create an AgentConfig in libs/vizu_agent_framework/src/.../config.py
MY_AGENT_CONFIG = AgentConfig(name="my_agent", ...)

# 2. Build and run in a new service
agent = AgentBuilder(MY_AGENT_CONFIG).with_llm().with_mcp().with_checkpointer().build()
```

---

## License

Proprietary — Vizu © 2025
