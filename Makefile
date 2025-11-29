# Makefile for common local development tasks (docker-compose aware)
# Usage: `make <target>`

COMPOSE=docker compose
DB_SERVICE=postgres
DB_USER=user
DB_NAME=vizu_db
# Host mapping: when running services on host, use localhost:5433 (common mapping)
HOST_DB_URL=postgresql://$(DB_USER):password@localhost:5433/$(DB_NAME)
COMPOSE_DB_URL=postgresql://$(DB_USER):password@postgres:5432/$(DB_NAME)

.PHONY: help compose-up compose-down build seed seed-check e2e-host shell-atendente add-dep-instructions

help:
	@echo "Available targets:"
	@echo "  compose-up            - Build and start docker compose (detached)"
	@echo "  compose-down          - Stop compose and remove containers"
	@echo "  build                 - Rebuild compose images (no cache)"
	@echo "  seed                  - Run the DB seed inside the dedicated container (uses service 'db_manager')"
	@echo "  seed-check            - Run a quick SQL check on the DB to confirm seeded rows"
	@echo "  e2e-host              - Run the e2e curl script on the host (exports PYTHONPATH)"
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
