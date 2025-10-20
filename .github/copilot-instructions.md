<!-- Short, focused guidance for AI coding agents working in the vizu-mono monorepo. -->
# Vizu monorepo — Copilot / AI agent instructions

These notes help an AI coding agent be productive quickly in this monorepo. They focus on concrete, discoverable patterns, file locations, and commands used by developers.

1) Big picture
- Monorepo layout: top-level folders split by responsibility:
  - services/ — runnable microservices (FastAPI + uvicorn, each with its own pyproject/Dockerfile).
  - libs/ — shared Python libraries kept alongside services and imported via PYTHONPATH or Poetry path dependencies.
  (all should be imported via Poetry)
  - infra/ and docker-configs/ — deployment and observability configs (OpenTelemetry collector, Docker compose).

- Typical runtime: each service is a Python app (3.11+) packed with Poetry and run with uvicorn in dev. Docker images copy a project-local .venv and set PYTHONPATH to include `/app/src` and `/app/libs`.

2) Where to look first (important files)
- Top-level: `docker-compose.yml` — canonical local dev composition and service names (postgres, redis, otel-collector, atendente_core, clients_api, clientes_finais_api, etc.).
- Service README examples: `services/atendente_core/README.md` — explains env vars and run/test commands.
- Dockerfile pattern: `services/atendente_core/Dockerfile` — multi-stage build, Poetry in builder, copies `.venv`, sets `PYTHONPATH`. Use this as the canonical Docker pattern for other services.
- Shared libs: `libs/` — examples: `vizu_db_connector`, `vizu_qdrant_client`, `vizu_shared_models`. These are referenced by services via PYTHONPATH or Poetry path deps.

3) Common developer workflows & commands
- Local dev with Docker Compose (recommended): `docker compose up --build` (uses `docker-compose.yml`). Service names from the compose file are important when wiring env vars.
- Running a service locally without Docker (common for quick iteration):
  - cd into service directory (for example `services/atendente_core`)
  - `poetry install`
  - copy `.env.example` -> `.env` and fill values
  - `poetry run uvicorn src.<service_package>.main:app --reload` (see `services/atendente_core/README.md`); or use the exact module path used in the Dockerfile (`atendente_core.main:app`).
- Tests: per-service `pytest` via Poetry: `poetry run pytest` when run from the service directory.

4) Project-specific conventions and patterns
- Python version: 3.11+ across services. Use Poetry for dependency management; many Dockerfiles rely on Poetry creating `.venv` inside the project (`POETRY_VIRTUALENVS_IN_PROJECT=true`).
- PYTHONPATH usage: docker-compose and Dockerfiles set `PYTHONPATH` to include `/app/src` and `/app/libs` (or service-specific equivalents). When running locally, ensure the interpreter can import packages in `libs/` (Poetry path deps or `PYTHONPATH` env).
- Entrypoint pattern in Dockerfiles: multi-stage builder to install deps, copy `.venv` into final image, then `CMD` calls python/uvicorn with package module path. Prefer to match the same import path when running locally.
- DB & infra: `docker-compose.yml` exposes development ports (Postgres on 5433 -> container 5432, Redis 6379, OTEL endpoints). `db_manager` service is a CLI-style container used for migrations and DB tasks.

5) Integration points & external dependencies
- Key external systems referenced in envs and configs:
  - Postgres (see `docker-compose.yml`)
  - Redis (session/state store)
  - OpenTelemetry collector (OTEL)
  - Ollama service (local model host) — `services/ollama_service`
  - Third-party APIs: Twilio, LangChain/LangGraph keys referenced in service READMEs/env examples

- When changing code that affects inter-service API contracts, update corresponding client libraries in `libs/` or the service tests that assert API contracts.

6) Code patterns & places to edit
- FastAPI apps: service entrypoints live under `services/*/src` and follow a package structure. E.g., `services/atendente_core/src/atendente_core/main.py` (module import path used by Dockerfile/uvicorn).
- Shared model types: `libs/vizu_shared_models/src` — prefer updating shared models here and bumping references where used.
- DB migrations / operations: `services/db_manager` and `libs/vizu_db_connector`.

7) Testing and CI notes
- CI workflows live under `.github/workflows/` (see repository). Per-service pytest runs are expected; use Poetry when running tests.
- If you change dependencies, update the service `pyproject.toml` and lock files (`poetry lock`) used by Dockerfile builder stage.

8) Helpful examples to reference in patches
- Use `services/atendente_core/Dockerfile` as the canonical multi-stage/Poetry/docker pattern.
- Use `docker-compose.yml` to discover service names, ports, and PYTHONPATH expectations.
- Use `services/atendente_core/README.md` for env var names and local run commands.

9) Safety & edit guidance for AI agents
- Keep changes minimal and focused per PR. Edit one service or one shared lib per branch where possible.
- When adding imports to services, ensure `libs/` packages are importable either by adding a Poetry path dependency or by ensuring PYTHONPATH includes the libs directory.
- Avoid changing Dockerfile multi-stage patterns unless you update the corresponding compose settings and README run commands.

If anything in these notes looks incomplete or you want examples for a particular service (tests, Dockerfile, or lib), tell me which service and I'll expand the doc with precise file paths and snippets.
