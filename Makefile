# =============================================================================
# Makefile for Vizu Mono - Development Environment
# =============================================================================
#
# Uso: make <target>
#
# Este Makefile centraliza todos os comandos de desenvolvimento do monorepo.
# Usa o .env da raiz como fonte única de configuração.
#
# =============================================================================

COMPOSE = docker compose
SHELL := /bin/bash

# Auto-load .env
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Defaults
SERVICE ?= atendente_core

.PHONY: help
.DEFAULT_GOAL := help

# =============================================================================
# HELP
# =============================================================================

help:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════════════╗"
	@echo "║               🚀 Vizu Mono - Development Commands                  ║"
	@echo "╚═══════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 DOCKER COMPOSE"
	@echo "   make up              Build and start all services"
	@echo "   make down            Stop and remove containers"
	@echo "   make restart         Restart SERVICE=<name> (default: atendente_core)"
	@echo "   make logs            Tail logs (all services)"
	@echo "   make logs s=<name>   Tail logs for specific service"
	@echo "   make ps              Show running containers"
	@echo "   make build           Rebuild all images (no cache)"
	@echo "   make build-s         Rebuild SERVICE=<name> only"
	@echo ""
	@echo "🗄️  DATABASE & MIGRATIONS"
	@echo "   make migrate         Apply migrations (local Docker)"
	@echo "   make migrate-prod    Apply migrations (Supabase - with confirmation)"
	@echo "   make migrate-status  Show current migration version"
	@echo "   make db-shell        Open psql shell"
	@echo ""
	@echo "🌱 SEEDS (Dados de Desenvolvimento)"
	@echo "   make seed            Run all seeds (DB + Qdrant)"
	@echo "   make seed-db         Seed only database (clients)"
	@echo "   make seed-qdrant     Seed only Qdrant (RAG knowledge)"
	@echo "   make seed-check      Verify current seed state"
	@echo ""
	@echo "🧪 TESTING"
	@echo "   make test            Run unit tests (atendente_core)"
	@echo "   make test-s          Run tests for SERVICE=<name>"
	@echo "   make test-all        Run tests for all services"
	@echo "   make chat            Quick chat test via curl"
	@echo "   make batch-run       Run batch test (10 messages, generates Langfuse traces)"
	@echo ""
	@echo "🔧 DEVELOPMENT"
	@echo "   make shell           Shell into SERVICE=<name> container"
	@echo "   make fmt             Format code (ruff) - services + libs"
	@echo "   make lint            Lint code (ruff check) - services + libs"
	@echo "   make lint-fix        Auto-fix lint issues (unused imports)"
	@echo "   make clean           Prune Docker cache"
	@echo ""
	@echo "📊 OBSERVABILITY"
	@echo "   make langfuse-check  Verify Langfuse connection"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Environment:"
	@echo "   SUPABASE_URL:    $(if $(SUPABASE_URL),✅ SET,❌ NOT SET)"
	@echo "   LANGFUSE_HOST:   $(if $(LANGFUSE_HOST),✅ $(LANGFUSE_HOST),❌ NOT SET)"
	@echo "   EMBEDDING_MODEL: $(if $(EMBEDDING_MODEL_NAME),$(EMBEDDING_MODEL_NAME),intfloat/multilingual-e5-large)"
	@echo ""

# =============================================================================
# DOCKER COMPOSE
# =============================================================================

.PHONY: up down restart logs ps build build-s

up:
	@echo "🚀 Starting all services..."
	$(COMPOSE) up --build -d
	@echo "✅ Services started. Use 'make logs' to tail logs."

down:
	@echo "🛑 Stopping services..."
	$(COMPOSE) down

restart:
	@echo "🔄 Restarting $(SERVICE)..."
	$(COMPOSE) restart $(SERVICE)
	@echo "✅ $(SERVICE) restarted"

logs:
ifdef s
	$(COMPOSE) logs -f --tail=100 $(s)
else
	$(COMPOSE) logs -f --tail=100
endif

ps:
	$(COMPOSE) ps

build:
	@echo "🔨 Building all images (no cache)..."
	$(COMPOSE) build --no-cache

build-s:
	@echo "🔨 Building $(SERVICE)..."
	$(COMPOSE) build --no-cache $(SERVICE)
	$(COMPOSE) up -d $(SERVICE)
	@echo "✅ $(SERVICE) rebuilt and started"

# =============================================================================
# DATABASE & MIGRATIONS
# =============================================================================

.PHONY: migrate migrate-prod migrate-status db-shell

migrate:
	@echo "🔄 Running migrations (local Docker)..."
	@docker exec vizu_atendente_core python -c "\
import sys; \
sys.path.insert(0, '/app/libs/vizu_db_connector/src'); \
sys.path.insert(0, '/app/libs/vizu_models/src'); \
from alembic.config import Config; \
from alembic import command; \
import os; \
cfg = Config('/app/libs/vizu_db_connector/alembic.ini'); \
cfg.set_main_option('sqlalchemy.url', os.environ['DATABASE_URL']); \
cfg.set_main_option('script_location', '/app/libs/vizu_db_connector/alembic'); \
command.upgrade(cfg, 'head'); \
print('✅ Migrations applied!')"

migrate-prod:
	@if [ -z "$(SUPABASE_DB_URL)" ]; then \
		echo "❌ SUPABASE_DB_URL not set in .env"; \
		exit 1; \
	fi
	@echo "⚠️  This will modify PRODUCTION database!"
	@echo "   URL: $$(echo '$(SUPABASE_DB_URL)' | sed 's/:.*@/:***@/')"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@cd libs/vizu_db_connector && \
		DATABASE_URL="$(SUPABASE_DB_URL)" \
		PYTHONPATH="$(PWD)/libs/vizu_models/src:$(PWD)/libs/vizu_db_connector/src" \
		poetry run alembic upgrade head
	@echo "✅ Migrations applied to Supabase!"

migrate-status:
	@echo "📊 Migration status..."
	@docker exec vizu_atendente_core python -c "\
from sqlalchemy import create_engine, text; \
import os; \
engine = create_engine(os.environ['DATABASE_URL']); \
conn = engine.connect(); \
result = conn.execute(text('SELECT version_num FROM alembic_version')); \
row = result.fetchone(); \
print('Current version:', row[0] if row else 'No migrations'); \
conn.close()"

db-shell:
	$(COMPOSE) exec -it postgres psql -U user -d vizu_db

# =============================================================================
# SEEDS
# =============================================================================

.PHONY: seed seed-db seed-qdrant seed-check

seed: seed-db seed-qdrant
	@echo "✅ All seeds completed!"

seed-db:
	@echo "🌱 Seeding database..."
	@docker exec -e PYTHONPATH=/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app \
		vizu_atendente_core python -m seeds.run_seeds --db

seed-qdrant:
	@echo "🌱 Seeding Qdrant..."
	@docker exec \
		-e PYTHONPATH=/app/libs/vizu_qdrant_client/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app \
		-e QDRANT_URL=http://qdrant_db:6333 \
		-e EMBEDDING_SERVICE_URL=http://embedding_service:11435 \
		vizu_atendente_core python -m seeds.run_seeds --qdrant

seed-check:
	@echo "📊 Checking seed state..."
	@docker exec \
		-e PYTHONPATH=/app/libs/vizu_qdrant_client/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app \
		-e QDRANT_URL=http://qdrant_db:6333 \
		vizu_atendente_core python -m seeds.run_seeds --check

# =============================================================================
# TESTING
# =============================================================================

.PHONY: test test-s test-all chat batch-run

test:
	@echo "🧪 Running tests for atendente_core..."
	cd services/atendente_core && poetry run pytest tests/ -v --tb=short

test-s:
	@echo "🧪 Running tests for $(SERVICE)..."
	cd services/$(SERVICE) && poetry run pytest tests/ -v --tb=short

test-all:
	@echo "🧪 Running all tests..."
	@for svc in atendente_core clients_api clientes_finais_api tool_pool_api; do \
		echo "Testing $$svc..."; \
		cd services/$$svc && poetry run pytest tests/ -v --tb=short 2>/dev/null || true; \
		cd ../..; \
	done

batch-run:
	@echo "🚀 Running batch test (generates Langfuse traces)..."
	@docker exec -e PYTHONPATH=/app \
		vizu_atendente_core python /app/scripts/batch_run.py

chat:
	@echo "💬 Testing chat endpoint..."
	@API_KEY=$$(docker exec vizu_atendente_core python /app/scripts/get_api_key.py 2>/dev/null) && \
	if [ -z "$$API_KEY" ]; then \
		echo "❌ No client found. Run 'make seed' first."; \
		exit 1; \
	fi && \
	echo "Using API Key: $${API_KEY:0:8}..." && \
	curl -s -X POST "http://localhost:8003/chat" \
		-H "Content-Type: application/json" \
		-H "X-API-KEY: $$API_KEY" \
		-d '{"message": "Olá, quais são os serviços disponíveis?", "session_id": "test-'$$(date +%s)'"}' | python3 -m json.tool 2>/dev/null || echo "❌ Request failed"

# =============================================================================
# DEVELOPMENT
# =============================================================================

.PHONY: shell fmt lint clean

shell:
	$(COMPOSE) exec $(SERVICE) bash

fmt:
	@echo "🎨 Formatting code..."
	@for dir in services/*/ libs/*/; do \
		if [ -f "$$dir/pyproject.toml" ]; then \
			echo "  Formatting $$dir..."; \
			(cd "$$dir" && poetry run ruff format . 2>/dev/null) || true; \
		fi \
	done
	@echo "✅ Done"

lint:
	@echo "🔍 Linting code..."
	@for dir in services/*/ libs/*/; do \
		if [ -f "$$dir/pyproject.toml" ]; then \
			echo "  Linting $$dir..."; \
			(cd "$$dir" && poetry run ruff check . 2>/dev/null) || true; \
		fi \
	done

lint-fix:
	@echo "🔧 Fixing lint issues (unused imports, etc)..."
	@for dir in services/*/ libs/*/; do \
		if [ -f "$$dir/pyproject.toml" ]; then \
			echo "  Fixing $$dir..."; \
			(cd "$$dir" && poetry run ruff check --fix --select F401,F841 . 2>/dev/null) || true; \
		fi \
	done
	@echo "✅ Done"

clean:
	@echo "🧹 Cleaning Docker cache..."
	docker builder prune -f
	docker image prune -f
	@echo "✅ Cleaned"

# =============================================================================
# OBSERVABILITY
# =============================================================================

.PHONY: langfuse-check langfuse-up langfuse-down langfuse-logs

langfuse-check:
	@echo "🔍 Checking Langfuse connection..."
	@docker exec vizu_atendente_core python /app/scripts/check_langfuse.py

langfuse-up:
	@echo "🚀 Starting local Langfuse..."
	@cd langfuse && docker compose up -d
	@echo "✅ Langfuse running at http://localhost:3000"
	@echo "📝 First time? Create account and project, then update .env with API keys"

langfuse-down:
	@echo "⏹️  Stopping local Langfuse..."
	@cd langfuse && docker compose down

langfuse-logs:
	@cd langfuse && docker compose logs -f --tail 50
