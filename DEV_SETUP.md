# Local Development Setup

## Overview

This guide helps you set up a **local development environment** that:

- ✅ Runs core services locally (dashboard, backend, tools)
- ✅ Connects to **remote Supabase** (no local database needed)
- ✅ Saves money by avoiding CI/CD on every change
- ✅ Enables fast iteration with hot-reload

## Prerequisites

1. **Docker Desktop** installed and running
2. **Make** installed (comes with macOS)
3. **`.env` file** configured in the repository root

## Environment Setup

### 1. Create your `.env` file

Copy from `.env.example` (if it exists) or create manually:

```bash
# Supabase (remote connection)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret

# LLM Provider (choose one)
LLM_PROVIDER=ollama_cloud  # or openai, anthropic, google
OLLAMA_CLOUD_API_KEY=your-key  # if using ollama_cloud
# OPENAI_API_KEY=your-key      # if using openai

# Frontend
VITE_SUPABASE_URL=${SUPABASE_URL}
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=http://localhost:8003
VITE_TOOL_POOL_API_URL=http://localhost:8006

# Optional: Langfuse observability (for tracing)
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
```

**Important:** The services will use **remote Supabase** via the REST API. No local PostgreSQL needed!

## Quick Start

### Start the dev stack:

```bash
make dev
```

This starts:
- 🎨 **vizu_dashboard** (React frontend) → http://localhost:8080
- 🤖 **atendente_core** (main LangGraph backend) → http://localhost:8003
- 🔧 **tool_pool_api** (MCP tool server) → http://localhost:8006
- 📦 **redis** (session storage)
- 🔍 **qdrant_db** (vector database for RAG)

### View logs:

```bash
make dev-logs
```

### Stop the stack:

```bash
make dev-down  # stops services but keeps containers
make down      # stops and removes containers
```

## Development Workflow

### 1. Code Changes

Your code is **hot-reloaded** via volume mounts:

```yaml
volumes:
  - ./apps/vizu_dashboard/src:/app/src  # Frontend hot-reload
  - ./services/atendente_core/src:/app/services/atendente_core/src  # Backend hot-reload
  - ./libs:/app/libs  # Shared libraries hot-reload
```

**Just edit and save** — changes apply automatically!

### 2. Testing Changes

```bash
# Quick health check
curl http://localhost:8003/health

# Test chat endpoint
make chat

# Test specific agents
make test-vendas
make test-support
```

### 3. Rebuild After Dependency Changes

If you modify `pyproject.toml` in any service:

```bash
make dev-down
make dev  # rebuilds with --build flag
```

Or rebuild a specific service:

```bash
make build-s SERVICE=atendente_core
```

## Database Workflow

### Your services automatically connect to Supabase REST API:

```python
from vizu_supabase_client.client import get_supabase_client

client = get_supabase_client()  # Uses SUPABASE_URL + SUPABASE_SERVICE_KEY
response = client.table("clientes_vizu").select("*").execute()
```

### Run migrations on Supabase:

```bash
make migrate-prod  # requires SUPABASE_DB_URL in .env
```

## Advanced: Full Stack Mode

Need **all** services (embedding, Langfuse, workers)?

```bash
make up                    # start everything
make up --profile local    # include local postgres too
```

This starts:
- All services from `make dev`
- `embedding_service` (HuggingFace embeddings)
- `file_upload_api` + `file_processing_worker`
- `vendas_agent` + `support_agent`
- And optionally with `--profile observability`:
  - `langfuse` (LLM tracing UI)
  - `otel-collector` (telemetry)

## Troubleshooting

### Service won't start:

```bash
# Check logs
make dev-logs

# Check specific service
make logs s=atendente_core

# Rebuild from scratch
docker compose build --no-cache atendente_core
make dev
```

### Supabase connection errors:

1. Verify `.env` has correct `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
2. Check your Supabase project is active
3. Verify IP allowlist (if using Supabase's network restrictions)

### Port conflicts:

```bash
# Check what's using ports
lsof -i :8080  # dashboard
lsof -i :8003  # atendente
lsof -i :8006  # tool_pool

# Stop conflicting services
make down
```

## Cost Savings

**Before:** Every push triggers GitHub Actions → Cloud Build → Cloud Run deployment ($$$)

**After:**
✅ Develop locally with `make dev`
✅ Test changes instantly
✅ Push only when ready for staging/prod
✅ Save 80%+ on CI/CD costs

## Next Steps

- 📖 Read [.github/copilot-instructions.md](.github/copilot-instructions.md) for architecture details
- 🧪 Check [ferramentas/evaluation_suite/](ferramentas/evaluation_suite/) for testing workflows
- 🔧 Explore [Makefile](Makefile) for all available commands

## Quick Reference

```bash
# Development
make dev              # start core services
make dev-down         # stop services
make dev-logs         # view logs

# Testing
make chat             # quick chat test
make smoke-test       # full E2E test
make test             # unit tests

# Database
make seed             # seed dev data
make migrate-prod     # migrate Supabase

# Full stack
make up               # all services
make down             # stop all
make ps               # show running containers
```

Happy coding! 🚀
