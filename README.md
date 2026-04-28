# Blu Mono

Monorepo for Blu platform services, shared libraries, dashboards, and infrastructure.

This repository combines:

- FastAPI microservices for orchestration, tool execution, and file ingestion
- Shared Python libraries for auth, context, SQL safety, RAG, connectors, and observability
- Frontend apps for dashboard, landing, and HITL operations
- Supabase schema and Edge Functions
- Local and Cloud Run oriented Docker Compose stacks

## What This Platform Does

Blu is a multi-tenant AI data platform focused on:

- Data analysis workflows for business teams
- Natural language to SQL with safety controls
- Hybrid RAG over tenant documents
- Agent orchestration with tool calling through MCP
- Secure tenant isolation through JWT and RLS

## Repository Layout

```text
apps/
  hitl_dashboard/         Streamlit app for human-in-the-loop operations
  landing/                Landing web app
  blu_dashboard/         Main React dashboard

services/
  atendente_core/         Main orchestration API (LangGraph-based)
  file_upload_api/        File upload and document processing API
  standalone_agent_api/   Standalone agent API
  tool_pool_api/          MCP tool server API

libs/
  blu_agent_framework/
  blu_auth/
  blu_context_service/
  blu_data_connectors/
  blu_db_connector/
  blu_elicitation_service/
  blu_experiment_service/
  blu_google_suite_client/
  blu_hitl_service/
  blu_llm_service/
  blu_models/
  blu_observability_bootstrap/
  blu_parsers/
  blu_prompt_management/
  blu_rag_factory/
  blu_shared_utils/
  blu_sql_factory/
  blu_supabase_client/
  blu_tool_registry/
  blu_twilio_client/

supabase/
  migrations/             SQL migrations
  functions/              Edge Functions

docs/                     Internal documentation and plans
scripts/                  Utility, seed, and automation scripts
tests/                    Cross-service and integration tests
```

## Architecture at a Glance

1. Frontend apps call service APIs.
2. `atendente_core` orchestrates requests, context, and agent/tool routes.
3. `tool_pool_api` exposes MCP tools used by agents.
4. Shared libraries provide reusable logic for auth, SQL safety, RAG, and connectors.
5. Supabase stores application data and enforces tenant isolation (RLS).
6. Redis supports caching and agent runtime state.

## Tech Stack

- Backend: Python 3.11+, FastAPI, SQLModel/Pydantic, LangGraph
- Frontend: React + TypeScript + Vite
- Data: Supabase/PostgreSQL, pgvector, Redis
- AI: Multi-provider LLM integration, hybrid retrieval pipeline
- Infra: Docker Compose (local), Cloud Run (deployment path), OpenTelemetry, Langfuse

## Prerequisites

Install these tools first:

- Docker and Docker Compose
- Make
- Python 3.11+
- (Optional) gcloud CLI for Cloud Run flows

## Environment Setup

The development stack expects a root `.env` file.

### 1. Create `.env`

Use the service template as a starting point:

```bash
cp services/atendente_core/.env.example .env
```

Then fill in required values for your environment. At minimum, confirm:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_JWT_JWK`
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` (or leave observability disabled where applicable)
- provider credentials for your selected `LLM_PROVIDER`

For frontend apps, set any required `VITE_*` values used by your workflow.

### 2. Optional Cloud Run env file

For Cloud Run compose testing, use:

```bash
cp .env.cloudrun.example .env.cloudrun
```

## Quick Start (Local Development)

Start the core development stack:

```bash
make dev
```

This starts the core services used for day-to-day development, including:

- landing app on http://localhost:8080
- dashboard app on http://localhost:8081
- atendente core on http://localhost:8003
- tool pool API on http://localhost:8006
- standalone agent API on http://localhost:8001

Stop the stack:

```bash
make dev-down
```

## Common Commands

### Development and logs

```bash
make dev
make dev-logs
make dev-rebuild
make ps
make logs
```

### Testing

```bash
make test
make test-all
make smoke-test
make batch-run
```

### Lint and format

```bash
make fmt
make lint
make lint-fix
```

### Database and migrations

```bash
make migrate
make migrate-status
make migrate-prod
```

### Seed and data utilities

```bash
make seed
make seed-db
make seed-check
```

Run `make help` for the full command catalog.

## Working with Supabase

- SQL migrations live in `supabase/migrations`.
- Additional migration support exists in `libs/blu_db_connector/alembic`.
- Root `supabase/config.toml` and `supabase/seed.sql` support local/managed workflows.

## Running Observability Components

The repository includes a local Langfuse stack in root compose files and a dedicated `langfuse/` workspace.

Use the observability profile when needed:

```bash
docker compose --profile observability up -d
```

## Development Notes

- Root `pyproject.toml` defines shared development tooling, not a distributable package.
- Each service/library can maintain its own local dependency configuration.
- Avoid committing secrets. Keep credentials in local `.env` files only.

## Security and Multi-Tenancy

Core safeguards in this codebase include:

- JWT-based request context extraction
- Row-Level Security in Supabase/PostgreSQL
- Tool-level validation and access constraints
- SQL validation and rewrite safeguards for text-to-SQL flows

## Contributing

1. Create a branch from `main`.
2. Implement changes with tests where relevant.
3. Run formatting, lint, and test commands locally.
4. Open a PR with context, risks, and rollout notes.

## Troubleshooting

- Run `make dev-logs` and `make logs s=<service_name>` for service-level logs.
- Check required env variables in `.env` first.
- Confirm Docker containers are healthy with `make ps`.
- For migration issues, inspect `make migrate-status` and Supabase migration state.

## License

Internal repository. Follow organizational policies for code usage and redistribution.
