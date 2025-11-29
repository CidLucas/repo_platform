# Makefile for common local development tasks (docker-compose aware)
# Usage: `make <target>`

COMPOSE=docker compose
DB_SERVICE=postgres
DB_USER=user
DB_NAME=vizu_db
# Host mapping: when running services on host, use localhost:5433 (common mapping)
HOST_DB_URL=postgresql://$(DB_USER):password@localhost:5433/$(DB_NAME)
COMPOSE_DB_URL=postgresql://$(DB_USER):password@postgres:5432/$(DB_NAME)

# When running migrations locally from the repo root, set PYTHONPATH so
# `vizu_models` and `vizu_db_connector` are importable without installing.
MIGRATION_PYTHONPATH?=$(PWD)/libs/vizu_models/src:$(PWD)/libs/vizu_db_connector/src

# E2E script settings
E2E_SCRIPT=ferramentas/e2e/run_jwt_smoke.sh
# E2E API-key script (host curl integration)
E2E_API_SCRIPT=services/atendente_core/tests/integration/e2e_auth_via_curl.sh
E2E_API_KEY?=
# Override with: make e2e-jwt SERVICE=atendente_core CLIENTE_VIZU_ID=<uuid>
SERVICE?=atendente_core
CLIENTE_VIZU_ID?=9930a61c-953e-47ba-86a2-c7ff03afe367

.PHONY: help compose-up compose-down build seed seed-check e2e-host shell-atendente add-dep-instructions

help:
	@echo "Available targets:"
	@echo "  compose-up            - Build and start docker compose (detached)"
	@echo "  compose-down          - Stop compose and remove containers"
	@echo "  build                 - Rebuild compose images (no cache)"
	@echo "  seed                  - Run the DB seed inside the dedicated container (uses service 'db_manager')"
	@echo "  seed-check            - Run a quick SQL check on the DB to confirm seeded rows"
	@echo "  e2e-host              - Run the e2e curl script on the host (exports PYTHONPATH)"
	@echo "  e2e-jwt               - Run the JWT e2e smoke script inside the atendente container"
	@echo "  shell-atendente       - Open a shell inside the atendente_core service container"
	@echo "  add-dep-instructions  - Print instructions to add Python deps (e.g., pyjwt) to a service and rebuild"

compose-up:
	$(COMPOSE) up --build -d

compose-down:
	$(COMPOSE) down

build:
	$(COMPOSE) build --no-cache

seed:
	@echo "Running seeder inside docker compose (db_manager service)..."
	$(COMPOSE) run --rm db_manager python -m vizu_db_connector.cli.seed

seed-check:
	@echo "Counting cliente_vizu rows (executes psql in postgres container)..."
	$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -c "SELECT count(*) FROM cliente_vizu;"

# Run the e2e script on the host. It will set PYTHONPATH to include local libs and services.
# Useful when you have local tooling installed. If you prefer to run inside compose, use 'compose-up' then exec.
e2e-host:
	@echo "Running e2e script on host with PYTHONPATH set for local libs..."
	@export PYTHONPATH=./libs/*/src:./services/atendente_core/src && \
	DATABASE_URL=${DATABASE_URL:-$(COMPOSE_DB_URL)} ./services/atendente_core/tests/integration/e2e_auth_via_curl.sh

.PHONY: e2e-jwt
e2e-jwt:
	@echo "Running JWT e2e smoke against service: $(SERVICE) (cliente_vizu_id=$(CLIENTE_VIZU_ID))"
	@chmod +x $(E2E_SCRIPT) || true
	@./$(E2E_SCRIPT) $(SERVICE) $(CLIENTE_VIZU_ID)

.PHONY: e2e-api-key
e2e-api-key:
	@echo "Running API-key e2e smoke against service: $(SERVICE) (cliente_vizu_id=$(CLIENTE_VIZU_ID))"
	@if [ -z "$(E2E_API_KEY)" ]; then \
		echo "ERROR: E2E_API_KEY is not set. Provide E2E_API_KEY=<key> or set as env var."; exit 1; \
	fi
	@echo "Using API key: ************${E2E_API_KEY:(-4)}"
	@export PYTHONPATH=./libs/*/src:./services/atendente_core/src && \
	E2E_API_KEY=$(E2E_API_KEY) CLIENTE_VIZU_ID=$(CLIENTE_VIZU_ID) ./$(E2E_API_SCRIPT)

# Open an interactive shell in the atendente_core service container
shell-atendente:
	$(COMPOSE) run --rm atendente_core bash

# Instructions for adding Python dependencies to a service and rebuilding images.
# NOTE: runtime images typically do not include 'poetry' CLI, so "docker compose run service poetry add <pkg>" may fail.
# Recommended: edit the service's pyproject.toml and rebuild the image.
add-dep-instructions:
	@echo "To add a Python dependency to a service (recommended):"
	@echo "  1) Edit the service pyproject: e.g. services/atendente_core/pyproject.toml"
	@echo "     add under [tool.poetry.dependencies]:\n       pyjwt = \"^2.8\""
	@echo "  2) Rebuild the service image: '$(COMPOSE) build atendente_core'"
	@echo "  3) Restart compose: '$(COMPOSE) up -d'"
	@echo "Alternative (if you have poetry locally):"
	@echo "  cd services/atendente_core && poetry add pyjwt && cd -"
	@echo "Do NOT run 'docker compose run atendente_core poetry add ...' against the runtime container; many runtime images don't include poetry."
.PHONY: migrate migrate-docker
migrate:
	@echo "Running DB migrations via libs/vizu_db_connector/run_migrations.py"
	@DATABASE_URL=${DATABASE_URL:-$(COMPOSE_DB_URL)} python ./libs/vizu_db_connector/run_migrations.py --db "${DATABASE_URL}"

# Run migrations inside an ephemeral docker python container (no local deps required).
# Useful in CI or when you don't have the project's venv.
migrate-docker:
	@echo "Running DB migrations inside ephemeral python:3.11-slim container"
	@docker run --rm \
		-e DATABASE_URL=${DATABASE_URL:-$(COMPOSE_DB_URL)} \
		-v $(PWD):/app -w /app/libs/vizu_db_connector python:3.11-slim bash -c "\
		apt-get update -qq && apt-get install -y --no-install-recommends wget ca-certificates build-essential libpq-dev || true && \
		python -m pip install --upgrade pip setuptools wheel && \
		python -m pip install alembic sqlalchemy sqlmodel psycopg2-binary && \
		python run_migrations.py --db \"$$DATABASE_URL\""

.PHONY: migrate-local
migrate-local:
	@if [ -z "${DATABASE_URL}" ]; then \
		echo "ERROR: DATABASE_URL is not set. Run: make migrate-local DATABASE_URL=postgresql://user:pw@host:5432/db"; exit 1; \
	fi
	@echo "Running DB migrations locally with PYTHONPATH=$(MIGRATION_PYTHONPATH)"
	@PYTHONPATH=$(MIGRATION_PYTHONPATH):$$PYTHONPATH python ./libs/vizu_db_connector/run_migrations.py --db "${DATABASE_URL}"

.PHONY: migrate-local-install
migrate-local-install:
	@echo "Installing local libs as editable packages into current Python environment (requires pip)"
	@python -m pip install --upgrade pip setuptools wheel
	@python -m pip install -e ./libs/vizu_models -e ./libs/vizu_db_connector || true
.PHONY: migrate-apply
migrate-apply:
	@echo "Run migrations against a target DB (e.g. SUPABASE). This requires SUPABASE_DB_URL or DATABASE_URL to be set."
	@if [ -z "${SUPABASE_DB_URL}${DATABASE_URL}" ]; then \
		echo "ERROR: set SUPABASE_DB_URL or DATABASE_URL before running migrate-apply"; exit 1; \
	fi
	@DBURL=${SUPABASE_DB_URL:-${DATABASE_URL:-$(COMPOSE_DB_URL)}}; \
		python ./libs/vizu_db_connector/run_migrations.py --db "$$DBURL"
