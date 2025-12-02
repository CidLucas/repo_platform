# Makefile for Vizu Mono - Local Development
# Usage: `make <target>`

COMPOSE=docker compose
DB_SERVICE=postgres
DB_USER=user
DB_NAME=vizu_db

# ============================================================================
# AUTO-LOAD .env FILE
# ============================================================================
# Carrega variáveis do .env automaticamente se existir
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Database URLs
LOCAL_DB_URL=postgresql://$(DB_USER):password@localhost:5433/$(DB_NAME)

COMPOSE_DB_URL=postgresql://$(DB_USER):password@postgres:5432/$(DB_NAME)

# Supabase - carregado do .env automaticamente via include acima
# No .env deve ter: SUPABASE_DB_URL=postgresql://postgres.xxx:password@host:port/postgres

# E2E test settings
SERVICE?=atendente_core
CLIENTE_VIZU_ID?=9930a61c-953e-47ba-86a2-c7ff03afe367

.PHONY: help

help:
	@echo "=== Vizu Ambiente de Desenvolvimento ==="
	@echo ""
	@echo "Docker Compose:"
	@echo "  up                    - Build and start all services"
	@echo "  down                  - Stop and remove containers"
	@echo "  build                 - Rebuild images (no cache)"
	@echo "  logs                  - Tail logs for all services"
	@echo "  logs-service          - Tail logs for SERVICE=<name>"
	@echo ""
	@echo "Database & Migrations:"
	@echo "  migrate               - Run migrations (local Docker)"
	@echo "  migrate-head          - Apply all pending migrations (Supabase - from .env)"
	@echo "  migrate-prod          - Same as migrate-head with confirmation"
	@echo "  migrate-status        - Show current migration version"
	@echo "  migrate-status-prod   - Show migration version (Supabase)"
	@echo "  db-shell              - Open psql shell"
	@echo ""
	@echo "Seeding:"
	@echo "  seed                  - Seed DB with test clients"
	@echo "  seed-update           - Update existing clients config"
	@echo "  seed-qdrant           - Seed Qdrant with RAG data"
	@echo "  seed-all              - Run all seeds (DB + Qdrant)"
	@echo "  seed-check            - Show seeded clients"
	@echo ""
	@echo "Batch Testing:"
	@echo "  batch-sample          - Create sample CSV"
	@echo "  batch-run             - Run batch test (uses local DB for API keys)"
	@echo "  batch-run-prod        - Run batch test (uses Supabase for API keys)"
	@echo ""
	@echo "Testing:"
	@echo "  test                  - Run pytest for atendente_core"
	@echo "  e2e                   - Run E2E smoke test"
	@echo ""
	@echo "Development:"
	@echo "  shell                 - Shell into atendente_core container"
	@echo "  rebuild               - Rebuild and restart SERVICE=<name>"
	@echo "  clean                 - Prune Docker cache"
	@echo ""
	@echo "Environment:"
	@echo "  SUPABASE_DB_URL is $(if $(SUPABASE_DB_URL),SET ✅,NOT SET ❌ - add to .env)"
	@echo ""

# ============================================================================
# DOCKER COMPOSE
# ============================================================================

.PHONY: up down build logs logs-service

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build --no-cache

logs:
	$(COMPOSE) logs -f --tail=100

logs-service:
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

# ============================================================================
# DATABASE & MIGRATIONS
# ============================================================================

.PHONY: migrate migrate-head migrate-prod migrate-status migrate-status-prod db-shell

# Local migrations (via Docker container)
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

# Supabase migrations - carrega do .env automaticamente
migrate-head:
	@if [ -z "$(SUPABASE_DB_URL)" ]; then \
		echo "❌ SUPABASE_DB_URL not set"; \
		echo ""; \
		echo "Add to your .env file:"; \
		echo "  SUPABASE_DB_URL=postgresql://postgres.xxxxx:password@host:port/postgres"; \
		echo ""; \
		echo "Or pass directly:"; \
		echo "  make migrate-head SUPABASE_DB_URL='postgresql://...'"; \
		exit 1; \
	fi
	@echo "🔄 Applying migrations to Supabase..."
	@echo "   URL: $$(echo '$(SUPABASE_DB_URL)' | sed 's/:.*@/:***@/')"
	@cd libs/vizu_db_connector && \
		DATABASE_URL="$(SUPABASE_DB_URL)" \
		PYTHONPATH="$(PWD)/libs/vizu_models/src:$(PWD)/libs/vizu_db_connector/src" \
		alembic upgrade head && \
		echo "✅ Migrations applied to Supabase!"

# Same as migrate-head but with confirmation prompt
migrate-prod:
	@if [ -z "$(SUPABASE_DB_URL)" ]; then \
		echo "❌ SUPABASE_DB_URL not set - add to .env or pass as argument"; \
		exit 1; \
	fi
	@echo "⚠️  This will modify PRODUCTION database!"
	@echo "   URL: $$(echo '$(SUPABASE_DB_URL)' | sed 's/:.*@/:***@/')"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(MAKE) migrate-head

# Status local
migrate-status:
	@echo "📊 Migration status (local)..."
	@docker exec vizu_atendente_core python -c "\
from sqlalchemy import create_engine, text; \
import os; \
engine = create_engine(os.environ['DATABASE_URL']); \
conn = engine.connect(); \
result = conn.execute(text('SELECT version_num FROM alembic_version')); \
row = result.fetchone(); \
print('Version:', row[0] if row else 'No migrations'); \
conn.close()"

# Status Supabase
migrate-status-prod:
	@if [ -z "$(SUPABASE_DB_URL)" ]; then \
		echo "❌ SUPABASE_DB_URL not set"; exit 1; \
	fi
	@echo "📊 Migration status (Supabase)..."
	@docker run --rm --network host \
		python:3.11-slim bash -c "\
			pip install -q psycopg2-binary sqlalchemy 2>/dev/null && \
			python -c \"\
from sqlalchemy import create_engine, text; \
engine = create_engine('$(SUPABASE_DB_URL)'); \
conn = engine.connect(); \
result = conn.execute(text('SELECT version_num FROM alembic_version')); \
row = result.fetchone(); \
print('Version:', row[0] if row else 'No migrations'); \
conn.close()\""

db-shell:
	$(COMPOSE) exec -it $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME)

# ============================================================================
# SEEDING
# ============================================================================

.PHONY: seed seed-update seed-qdrant seed-all seed-check

seed:
	@echo "🌱 Seeding DB..."
	@docker exec vizu_atendente_core python -c "\
import sys; \
sys.path.insert(0, '/app/libs/vizu_db_connector/src'); \
sys.path.insert(0, '/app/libs/vizu_models/src'); \
import os; \
from vizu_db_connector.cli.seed import run_LOCAL_DATABASE; \
run_LOCAL_DATABASE(os.environ['DATABASE_URL'])"

seed-update:
	@echo "🔄 Updating clients..."
	@docker exec vizu_atendente_core python -c "\
import sys; \
sys.path.insert(0, '/app/libs/vizu_db_connector/src'); \
sys.path.insert(0, '/app/libs/vizu_models/src'); \
import os; \
from vizu_db_connector.cli.update_clients import run_update; \
run_update(os.environ['DATABASE_URL'])"

seed-qdrant:
	@echo "🌱 Seeding Qdrant..."
	@docker exec -e QDRANT_URL=http://qdrant_db:6333 -e OPENAI_API_KEY=$(OPENAI_API_KEY) \
		vizu_atendente_core python -c "\
import sys; \
sys.path.insert(0, '/app/libs/vizu_qdrant_client/src'); \
from vizu_qdrant_client.cli.seed_qdrant import run_seed; \
run_seed()"

seed-all: seed seed-qdrant
	@echo "✅ All seeds completed!"

seed-check:
	@echo "📊 Checking clients..."
	$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -c "\
		SELECT nome_empresa, tier, ferramenta_rag_habilitada, collection_rag \
		FROM cliente_vizu ORDER BY nome_empresa;"

# ============================================================================
# BATCH TESTING
# ============================================================================

.PHONY: batch-sample batch-run batch-run-prod

batch-sample:
	@echo "📝 Creating sample CSV..."
	@cd ferramentas && python3 batch_requests.py --create-sample 2>/dev/null || \
		docker exec vizu_atendente_core python /app/ferramentas/batch_requests.py --create-sample

# Run batch via Docker container (has all dependencies)
batch-run:
	@echo "🧪 Running batch tests (local DB via Docker)..."
	@docker exec -w /app/ferramentas vizu_atendente_core python batch_requests.py \
		--csv mensagens_teste.csv \
		--db-url "postgresql://user:password@postgres:5432/vizu_db" \
		--verbose \
		--output batch_results.csv
	@echo "📊 Results saved to ferramentas/batch_results.csv"

batch-run-prod:
	@if [ -z "$(SUPABASE_DB_URL)" ]; then \
		echo "❌ SUPABASE_DB_URL not set"; exit 1; \
	fi
	@echo "🧪 Running batch tests (Supabase via Docker)..."
	@docker exec -e SUPABASE_DB_URL="$(SUPABASE_DB_URL)" -w /app/ferramentas vizu_atendente_core python batch_requests.py \
		--csv mensagens_teste.csv \
		--supabase \
		--verbose \
		--output batch_results_prod.csv

# ============================================================================
# TESTING
# ============================================================================

.PHONY: test e2e

test:
	@echo "🧪 Running tests..."
	cd services/atendente_core && poetry run pytest tests/ -v --tb=short

e2e:
	@echo "🧪 Running E2E smoke..."
	@chmod +x ferramentas/e2e/run_jwt_smoke.sh 2>/dev/null || true
	@./ferramentas/e2e/run_jwt_smoke.sh $(SERVICE) $(CLIENTE_VIZU_ID)

# ============================================================================
# DEVELOPMENT
# ============================================================================

.PHONY: shell rebuild clean

shell:
	$(COMPOSE) run --rm atendente_core bash

rebuild:
	@echo "🔄 Rebuilding $(SERVICE)..."
	$(COMPOSE) build --no-cache $(SERVICE)
	$(COMPOSE) up -d $(SERVICE)
	@echo "✅ $(SERVICE) rebuilt!"

clean:
	@echo "🧹 Cleaning Docker cache..."
	docker builder prune -f
	docker image prune -f
	@echo "✅ Cleaned!"
