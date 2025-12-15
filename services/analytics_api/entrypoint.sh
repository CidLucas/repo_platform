#!/bin/sh
# Build PYTHONPATH from all libs/*/src directories so package imports work
LIB_PATHS=""
for d in /app/libs/*/src; do
  if [ -d "$d" ]; then
    if [ -z "$LIB_PATHS" ]; then
      LIB_PATHS="$d"
    else
      LIB_PATHS="$LIB_PATHS:$d"
    fi
  fi
done
export PYTHONPATH="src${LIB_PATHS:+:$LIB_PATHS}"

# Ensure venv binaries are in PATH (venv is copied to service path)
export PATH="/app/services/analytics_api/.venv/bin:$PATH"

exec /app/services/analytics_api/.venv/bin/uvicorn analytics_api.main:app --host 0.0.0.0 --port ${PORT:-8000}
