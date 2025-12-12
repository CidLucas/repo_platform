<!-- Short, focused guidance for AI coding agents working in the vizu-mono monorepo. -->
# Vizu monorepo — Copilot / AI agent instructions

**Last Updated:** December 2025

These notes help an AI coding agent be productive quickly in this monorepo. They focus on concrete, discoverable patterns, file locations, and commands used by developers.

## 1) Big Picture

**Monorepo Layout:**
- `services/` — Runnable microservices:
  - **Agents pool:** `atendente_core` (main LLM/agentic entry), `tool_pool_api` (tool definitions), `vendas_agent`, `support_agent`
  - **Workers pool:** `data_ingestion_worker`, `file_processing_worker`, `file_upload_api`
  - **Supporting services:** `analytics_api`, `data_ingestion_api`, `embedding_service`, `migration_runner`, `ollama_service`
  - Each service has its own `pyproject.toml`, `Dockerfile`, and optional `.env.example`
- `libs/` — Shared Python libraries imported via Poetry path dependencies:
  - `vizu_db_connector` — database/migrations CLI
  - `vizu_models` — shared Pydantic models
  - `vizu_agent_framework` — LLM/tool orchestration
  - `vizu_llm_service` — LLM provider abstraction
  - `vizu_observability_bootstrap` — Langfuse/OTEL instrumentation
  - And others for specific domains (auth, elicitation, context, etc.)
- `apps/` — Frontend applications (`vizu_dashboard` — React/TypeScript with nginx)
- `.github/workflows/` — CI/CD automation (`ci.yml` for linting, `deploy-cloud-run.yml` for GCP deployments)

**Typical Runtime:**
- Each service is a Python 3.11+ FastAPI/uvicorn app.
- Docker images use multi-stage builds: Poetry in builder stage, `.venv` copied to final runtime stage.
- `PYTHONPATH` in Dockerfile includes service source code and lib paths (relative: `src:../../libs/*/src`).

## 2) Where to Look First

**Important Files:**
- `docker-compose.yml` — **canonical local dev config**. Defines all services, environment variables, networking, volumes, and service dependencies. Service names here (e.g., `atendente_core`, `redis`, `postgres`) must match in `.env` and code configs.
- `docker-compose.prod.yml` — production overrides (resource limits, restart policies, etc.)
- `.github/workflows/ci.yml` — **linting, building, and testing** (runs ruff, checks pyproject.toml syntax, builds Docker images for all services)
- `.github/workflows/deploy-cloud-run.yml` — **GCP Artifact Registry deployment** (pushes to `us-east1-docker.pkg.dev`)
- Service READMEs: `services/*/README.md` — explains env vars, local run commands, and service-specific setup
- Dockerfile pattern: `services/atendente_core/Dockerfile` — **canonical multi-stage pattern** used across all Python services (builder stage with Poetry, runtime stage with copied `.venv` and code)
- `libs/vizu_db_connector/` — database migrations CLI and connection utilities

## 3) Common Developer Workflows & Commands

**Local Dev with Docker Compose:**
```bash
docker compose up --build -d  # Start all services with rebuild
docker compose logs <service> # View logs for a service
docker compose down -v        # Stop all and remove volumes
```

**Running a Service Locally (without Docker, for quick iteration):**
```bash
cd services/atendente_core
poetry install                                      # Install deps
cp .env.example .env                               # Create .env
# Edit .env with required values
poetry run uvicorn atendente_core.main:app --reload  # Start service
```

**Testing:**
```bash
cd services/<service>
poetry run pytest                 # Run all tests
poetry run pytest src/tests/test_*.py -v  # Run specific tests with verbose output
```

**Linting & Code Quality:**
```bash
# From root:
poetry run ruff check .          # Run ruff linter
poetry run ruff check . --fix    # Auto-fix issues
poetry run ruff format .         # Format code

# For a specific service:
cd services/analytics_api
poetry run ruff check src/
poetry run ruff check src/ --fix
```

**Build & Push Docker Images:**
```bash
# Build locally (test):
docker build -t vizu-analytics-api:test -f services/analytics_api/Dockerfile .

# Build and tag for GitHub Container Registry:
docker build -t ghcr.io/vizubr/analytics-api:latest -f services/analytics_api/Dockerfile .

# Authenticate and push:
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin
docker push ghcr.io/vizubr/analytics-api:latest
```

## 4) Project-Specific Conventions & Patterns

**Python & Dependencies:**
- Python version: 3.11+ across all services
- Dependency management: **Poetry** (mandatory for all services)
- Virtual environments: Set `POETRY_VIRTUALENVS_IN_PROJECT=true` in Dockerfile builder stage to create `.venv` inside the project root
- Lock files: Always commit `poetry.lock` after modifying `pyproject.toml`

**PYTHONPATH & Import Paths:**
- Dockerfiles set `PYTHONPATH` to include service source and lib paths (e.g., `src:../../libs/vizu_db_connector/src`)
- When running locally, Poetry path dependencies handle lib imports automatically
- Services import from libs as: `from vizu_db_connector.database import get_db_session`
- Never hardcode absolute paths; use relative paths in PYTHONPATH

**Dockerfile Multi-Stage Pattern:**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install poetry==1.8.0
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
COPY ./libs ./libs
COPY ./services/<service> ./services/<service>
WORKDIR /app/services/<service>
RUN poetry install --no-root

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app/services/<service>
COPY --from=builder /app/services/<service>/.venv ./.venv
COPY --from=builder /app/libs /app/libs
COPY --from=builder /app/services/<service>/src ./src
ENV PATH="/app/services/<service>/.venv/bin:$PATH"
ENV PYTHONPATH="src:../../libs/vizu_db_connector/src"
EXPOSE 8000
CMD ["uvicorn", "service_package.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Code Quality Standards:**
- All Python code must pass `ruff check` (enforced in CI)
- Use modern type hints: `X | None` instead of `Optional[X]` (UP045 rule)
- Imports must be sorted (I001 rule enforced)
- Max line length: 88 characters (ruff default)

**Database & Infrastructure:**
- `docker-compose.yml` exposes:
  - PostgreSQL: host `postgres:5432` (mapped to 5432 internally, 5432 in services)
  - Redis: host `redis:6379`
  - OTEL Collector: `otel-collector:4317`
- `vizu_db_connector` provides: `get_db_session()` for dependency injection
- Database URL format: `postgresql://user:password@host:port/db_name`

## 5) Integration Points & External Dependencies

**Key External Systems:**
- **PostgreSQL**: Main database (local: `postgres:5432`, production: Supabase)
- **Redis**: Cache and session store (`redis:6379`)
- **OpenTelemetry Collector**: Observability pipeline (`otel-collector:4317`)
- **Langfuse**: LLM observability and traces (local: `http://host.docker.internal:3000`, cloud: `https://us.cloud.langfuse.com`)
- **Ollama**: Local LLM inference (`ollama_service:11434`)
- **Third-party APIs**: Twilio, LangChain/LangGraph, Google APIs (keys in `.env`)

**Service Communication:**
- Services use `http://<service_name>:<port>` for internal communication (e.g., `http://tool_pool_api:8000/tools`)
- `BASE_URL` environment variable: points to `atendente_core` (main entry point)
- When modifying service APIs, update all dependent services and their tests

## 6) Code Patterns & Places to Edit

**FastAPI Services:**
- Service entrypoints: `services/<service>/src/<service>/main.py`
- Package structure: `services/<service>/src/<service>/` contains app modules
- Routers: `services/<service>/src/<service>/api/router.py` or `endpoints/`
- Dependencies: `services/<service>/src/<service>/api/dependencies.py` for DI
- Database access: `services/<service>/src/<service>/data_access/` layer
- Services: `services/<service>/src/<service>/services/` business logic layer

**Shared Patterns:**
- Pydantic models: `libs/vizu_models/src/vizu_models/`
- Database utilities: `libs/vizu_db_connector/src/vizu_db_connector/`
- Observability: `libs/vizu_observability_bootstrap/src/` (Langfuse/OTEL setup)
- Agent framework: `libs/vizu_agent_framework/src/` (LLM/tool orchestration)

**Frontend:**
- React dashboard: `apps/vizu_dashboard/` (Node.js, built to `/dist`)
- Nginx config: `apps/vizu_dashboard/nginx.conf` (SPA routing)

## 7) Testing and CI

**Local Testing:**
```bash
cd services/<service>
poetry run pytest                 # Run all tests
poetry run pytest src/tests/ -v   # Verbose output
```

**CI Pipeline (`.github/workflows/ci.yml`):**
1. **Lint Check**: Runs `ruff check` on entire codebase (excludes `langfuse/`, `ferramentas/`)
2. **Dependency Check**: Validates all `pyproject.toml` files have correct syntax
3. **Docker Build**: Builds images for all services in the matrix:
   - Agents pool: `atendente_core`, `tool_pool_api`, `vendas_agent`, `support_agent`
   - Workers pool: `data_ingestion_worker`, `file_processing_worker`, `file_upload_api`
   - Frontend: `vizu_dashboard` (from `apps/`)
4. **Image Size Check**: Fails if any image exceeds 500MB

**Deployment Pipeline (`.github/workflows/deploy-cloud-run.yml`):**
- Triggered on: push to `main` (if `services/` or `libs/` changed), or manual workflow dispatch
- Builds and pushes images to GCP Artifact Registry: `us-east1-docker.pkg.dev`
- Requires secrets: `GCP_PROJECT_ID`, `GCP_SA_KEY`, `GCP_SA_EMAIL`
- Deploys agents-pool and workers-pool services

## 8) Helpful Examples to Reference in Patches

- Use `services/atendente_core/Dockerfile` as the canonical multi-stage/Poetry/docker pattern.
- Use `docker-compose.yml` to discover service names, ports, and PYTHONPATH expectations.
- Use `services/atendente_core/README.md` for env var names and local run commands.
- Reference `.github/workflows/ci.yml` for understanding the build and lint pipeline.
- Check `libs/vizu_db_connector/src/vizu_db_connector/database.py` for standard DB session patterns.

## 9) Safety & Edit Guidance for AI Agents

- Keep changes minimal and focused per PR. Edit one service or one shared lib per branch where possible.
- When adding imports to services, ensure `libs/` packages are importable either by adding a Poetry path dependency or by ensuring PYTHONPATH includes the libs directory.
- Avoid changing Dockerfile multi-stage patterns unless you update the corresponding compose settings and README run commands.
- **Always run `poetry lock` after modifying `pyproject.toml`** in a service to update `poetry.lock`.
- Run `ruff check . --fix` to auto-fix import sorting and type annotation issues before committing.
- Verify lint passes locally with `poetry run ruff check src/` before pushing.

If anything in these notes looks incomplete or you want examples for a particular service (tests, Dockerfile, or lib), tell me which service and I'll expand the doc with precise file paths and snippets.

## 10) Recent Changes & Architecture Updates (December 2025)

**Analytics API Service (New):**
- Added new `services/analytics_api` for aggregated metrics and dashboards
- Implements cache service using Redis for query optimization
- Multi-period metrics: today, yesterday, week, month, quarter, year
- Includes growth rate calculations and comparative analytics
- Example Dockerfile follows multi-stage pattern with Poetry (.venv in builder)

**Lint & Type Annotation Fixes:**
- Migrated all `Optional[X]` to `X | None` modern syntax (UP045 rule)
- Fixed import sorting across all services (I001 rule)
- All services now pass `ruff check` with UP045 and I001 rules enabled

**Docker & Build Improvements:**
- Canonical Dockerfile pattern uses absolute PYTHONPATH in runtime stage
- Services copy `.venv` from builder to avoid shebang issues
- All lib paths resolved with relative paths: `../../libs/<lib>/src`
- Image size checks enforced: max 500MB per image (analytics_api: 92.3MB)

**CI/CD Pipeline:**
- `ci.yml`: Runs ruff linting, pyproject.toml syntax check, Docker builds for all services
- `deploy-cloud-run.yml`: Manages GCP Artifact Registry push with proper image tagging
- Supports manual workflow dispatch for selective service deployment

## 11) Guidance for Future Agents Working on This Repo

**Before Changing Any Tool Schema:**
- Verify where `cliente_id` is created and validated (search for `InternalClientContext` / `_internal_context`)
- Server should be the source of truth for client identifiers — never rely on LLM-provided IDs

**When Adding/Updating Tools:**
- Prefer a thin wrapper that exposes only safe parameters to the LLM (e.g., `query`)
- Keep authentication/context injection server-side

**Async & Performance:**
- Use `asyncio` and `async` interfaces where possible for tools to enable parallel execution
- If a tool is sync-only, prefer exposing an `ainvoke` wrapper or use `asyncio.to_thread`
- Avoid blocking the event loop in async contexts

**Observability & Tracing:**
- Instrument both tool execution and the supervisor steps with Langfuse
- Include `tool_call_id` and `session_id` in spans for trace correlation

**Dependency Management:**
- When modifying libs under `libs/`, update their `pyproject.toml` and run `poetry lock` in affected service(s)
- Keep `poetry.lock` in sync to ensure Docker builder determinism

## 12) Quick Run Checklist (Local Dev)

- Ensure `.env` contains `LLM_PROVIDER`, `LANGFUSE_HOST`, and any LLM API keys needed
- Start infra: `docker compose up --build -d`
- Confirm services: `docker compose logs tool_pool_api --tail=50` and `docker compose logs atendente_core --tail=50`
- Run a quick chat: `make chat` (uses API key from seeded DB)
- Generate traces: `make batch-run` (runs inside container and writes traces to Langfuse)

## 13) Troubleshooting & Common Issues

**Docker Build Failures:**
- If `poetry install` fails in builder: ensure `poetry.lock` is valid (no merge conflicts)
- Use `poetry lock` to regenerate if corrupted
- Check that all path dependencies in `pyproject.toml` point to existing lib directories

**Import Errors in Services:**
- Verify `PYTHONPATH` matches Dockerfile: e.g., `src:../../libs/vizu_db_connector/src`
- Ensure all libs are listed as path dependencies in service `pyproject.toml`
- Run `poetry install` locally to validate dependency resolution

**Port Conflicts:**
- Check `docker-compose.yml` for port mappings
- Use `docker compose down -v` to fully clean up before rebuilding
- Verify no services are running on conflicting ports: `lsof -i :<port>`

**CI/CD Secrets:**
- For GitHub Container Registry: ensure GITHUB_TOKEN has `write:packages` permission
- For GCP: verify `GCP_SA_KEY` is valid JSON and `GCP_PROJECT_ID` matches the registry project
- Use `docker logout ghcr.io` and re-authenticate if push fails
