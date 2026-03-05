#!/usr/bin/env zsh
# End-to-end curl test for `atendente_core` authentication flows.
#
# Usage (from repo root):
#   chmod +x services/atendente_core/tests/integration/e2e_auth_via_curl.sh
#   ./services/atendente_core/tests/integration/e2e_auth_via_curl.sh
#
# This script demonstrates the steps to:
# 1) seed a test `cliente_vizu` row in your Postgres (uses $DATABASE_URL from repo .env)
# 2) start the atendente_core server (uvicorn) in the background
# 3) call the `/chat` endpoint via `curl` using API-Key and JWT flows
# 4) show responses, then teardown the server
#
# Prerequisites:
# - `psql` on PATH (for seeding) OR adapt the SQL seeding step to your preferred client
# - `python` with project deps (or use the docker-compose described in repo README)
# - repo `.env` populated (contains `DATABASE_URL` and `SUPABASE_JWT_SECRET`)

set -euo pipefail

# Helper: locate repo root from this script's dir (4 levels up from tests/integration)
REPO_ROOT=$(cd "$(dirname "$0")/../../../../" && pwd)
echo "Repo root: $REPO_ROOT"

# Load repo .env if present
if [ -f "$REPO_ROOT/.env" ]; then
  echo "Loading .env"
  set -a
  source "$REPO_ROOT/.env"
  set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  # Default to the Docker Compose service name (useful when running inside
  # a development container or when the repo is run via docker-compose).
  DATABASE_URL="postgresql://user:password@postgres:5432/vizu_db"
  echo "DATABASE_URL not provided; defaulting to Docker Compose DB: $DATABASE_URL"
  echo "Note: When running from the host shell you may need to use localhost:5433 instead."
fi

TEST_API_KEY="e2e_test_api_key_$(date +%s)"
TEST_CLIENT_NAME="E2E Test Client"
TEST_UUID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

echo "Seeding test client into database (id=$TEST_UUID api_key=$TEST_API_KEY)"

read -r -d '' SQL <<SQL || true
INSERT INTO cliente_vizu (id, nome_empresa, enabled_tools)
VALUES ('$TEST_UUID', '$TEST_CLIENT_NAME', ARRAY['executar_rag_cliente', 'executar_sql_agent'])
ON CONFLICT (id) DO NOTHING;
SQL

if command -v psql >/dev/null 2>&1; then
  echo "Running psql to seed client..."
  # psql will accept a full DATABASE_URL
  echo "$SQL" | psql "$DATABASE_URL"
else
  echo "Warning: psql not found. Skipping automatic DB seeding." >&2
  echo "SQL to run manually:" >&2
  echo "$SQL" >&2
fi

# Start server (background) unless the user has ATENDENTE_E2E_SKIP_SERVER=true
if [ "${ATENDENTE_E2E_SKIP_SERVER:-false}" = "true" ]; then
  echo "Skipping server start (ATENDENTE_E2E_SKIP_SERVER=true)"
else
  echo "Starting atendente_core with uvicorn (background)..."
  cd "$REPO_ROOT/services/atendente_core" || exit 1

  # Ensure local libs and services are importable for the uvicorn process
  # Add each lib's src directory to PYTHONPATH so package imports resolve
  LIB_SRCS=$(find "$REPO_ROOT/libs" -maxdepth 2 -type d -name src 2>/dev/null | paste -sd ':' -)
  if [ -n "$LIB_SRCS" ]; then
    export PYTHONPATH="$LIB_SRCS:$REPO_ROOT/services:${PYTHONPATH:-}"
  else
    export PYTHONPATH="$REPO_ROOT/libs:$REPO_ROOT/services:${PYTHONPATH:-}"
  fi

  # Provide minimal runtime env defaults so the app's pydantic Settings can initialize.
  export REDIS_URL="${REDIS_URL:-redis://redis:6379}"
  export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
  export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-}"
  # Start via poetry if available, else python -m uvicorn
  if command -v poetry >/dev/null 2>&1; then
    poetry run uvicorn atendente_core.main:app --host 127.0.0.1 --port 8000 &
  else
    python3 -m uvicorn atendente_core.main:app --host 127.0.0.1 --port 8000 &
  fi
  SERVER_PID=$!
  echo "uvicorn pid=$SERVER_PID"

  # wait for health endpoint
  echo -n "Waiting for server to become healthy"
  for i in {1..30}; do
    if curl -sSf http://127.0.0.1:8000/health >/dev/null 2>&1; then
      echo " -> healthy"
      break
    fi
    echo -n "."
    sleep 1
  done
fi

echo
echo "=== CURL: API-Key flow ==="
  curl -sS -X POST "http://127.0.0.1:8000/chat" \
    -H "Content-Type: application/json" \
    -H "X-Vizu-API-Key: $TEST_API_KEY" \
    -d '{"session_id":"s1","message":"Olá, teste via API key"}' || true

echo
echo "=== CURL: JWT flow ==="
if [ -z "${SUPABASE_JWT_SECRET:-}" ]; then
  echo "SUPABASE_JWT_SECRET not set, cannot build a valid JWT. Skipping JWT test." >&2
else
  # Only attempt to build JWT if python3 has the 'jwt' module available
  if python3 -c "import jwt" >/dev/null 2>&1; then
    echo "Building temporary JWT (sub=external-e2e)"
    JWT=$(python3 - <<PY
import os, jwt
secret=os.environ.get('SUPABASE_JWT_SECRET')
payload={"sub":"external-e2e","exp":9999999999}
print(jwt.encode(payload, secret, algorithm='HS256'))
PY
)

    curl -sS -X POST "http://127.0.0.1:8000/chat" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $JWT" \
      -d '{"session_id":"s2","message":"Olá, teste via JWT"}' || true
  else
    echo "python3 does not have 'jwt' installed; skipping JWT request." >&2
  fi
fi

# Teardown
if [ -n "${SERVER_PID:-}" ]; then
  echo "Stopping uvicorn pid=$SERVER_PID"
  kill $SERVER_PID || true
fi

echo "E2E curl script finished. Inspect responses above."
