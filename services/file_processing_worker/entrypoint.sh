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

exec /app/services/file_processing_worker/.venv/bin/uvicorn file_processing_worker.main:app --host 0.0.0.0 --port ${PORT:-8000}
