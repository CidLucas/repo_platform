#!/usr/bin/env bash
# Sync app_config.agent_api_core_url to the CURRENT ngrok tunnel URL.
#
# Why: the prod pg_cron `dispatch_routine_executions` POSTs dispatched routine
# executions to <agent_api_core_url>/internal/routines/run-dispatched — which in
# dev is your LOCAL agent_api exposed via ngrok. ngrok free-tier URLs change on
# every restart, so after (re)starting ngrok you must repoint app_config or every
# dispatch hits ngrok's 404 page and executions get stuck 'dispatched' → 'failed'.
#
# Usage:
#   1. Start your tunnel:  ngrok http 8003
#   2. Run:                ./scripts/sync-ngrok-agent-api-url.sh
#
# Reads DATABASE_URL_DIRECT from .env (strips the +psycopg2 sqlalchemy dialect).
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

# Find the ngrok web API (default 4040; ngrok picks 4041+ if 4040 is taken).
NGROK_URL=""
for port in 4040 4041 4042; do
  resp="$(curl -s -m 3 "http://localhost:${port}/api/tunnels" 2>/dev/null || true)"
  [ -z "$resp" ] && continue
  NGROK_URL="$(printf '%s' "$resp" | python3 -c "import sys,json
try:
    d=json.load(sys.stdin)
    print(next(t['public_url'] for t in d.get('tunnels',[]) if t['public_url'].startswith('https')))
except Exception:
    pass" 2>/dev/null || true)"
  [ -n "$NGROK_URL" ] && break
done

if [ -z "$NGROK_URL" ]; then
  echo "ERROR: no ngrok https tunnel found on :4040-4042. Is 'ngrok http 8003' running?" >&2
  exit 1
fi

DBURL="$(grep -E '^DATABASE_URL_DIRECT=' .env | head -1 | cut -d= -f2- | tr -d '"' | sed 's/+psycopg2//')"
if [ -z "$DBURL" ]; then echo "ERROR: DATABASE_URL_DIRECT not found in .env" >&2; exit 1; fi

NEW_VALUE="${NGROK_URL}/v1"
psql "$DBURL" -v ON_ERROR_STOP=1 -c \
  "update app_config set value='${NEW_VALUE}' where key='agent_api_core_url';" >/dev/null

echo "✅ agent_api_core_url -> ${NEW_VALUE}"
