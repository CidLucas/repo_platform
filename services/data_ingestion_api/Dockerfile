# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true


WORKDIR /app
RUN pip install poetry==1.8.0

# Copy ONLY required libs (check pyproject.toml for exact list)
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_supabase_client libs/vizu_supabase_client
COPY libs/vizu_auth libs/vizu_auth
COPY libs/vizu_data_connectors libs/vizu_data_connectors

# Copy service files
COPY services/data_ingestion_api services/data_ingestion_api

WORKDIR /app/services/data_ingestion_api

# Install dependencies WITHOUT dev packages
RUN poetry install --no-root

# Stage 2: Runtime (minimal - NO POETRY!)
FROM python:3.11-slim AS final

WORKDIR /app/services/data_ingestion_api

# Set PATH and PYTHONPATH
ENV PATH="/app/services/data_ingestion_api/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/data_ingestion_api/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app/libs/vizu_supabase_client/src:/app/libs/vizu_auth/src"

# Copy .venv from builder (preserves shebangs)
COPY --from=builder /app/services/data_ingestion_api/.venv ./.venv

# Copy ONLY lib src directories (not tests, docs, etc.)
COPY --from=builder /app/libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/libs/vizu_supabase_client/src /app/libs/vizu_supabase_client/src
COPY --from=builder /app/libs/vizu_auth/src /app/libs/vizu_auth/src
COPY --from=builder /app/libs/vizu_data_connectors/src /app/libs/vizu_data_connectors/src

# Copy service source code
COPY --from=builder /app/services/data_ingestion_api/src ./src

EXPOSE 8000

# Direct uvicorn call (NO poetry run - saves ~50MB by not needing Poetry in runtime)
CMD ["/bin/sh", "-c", "/app/services/data_ingestion_api/.venv/bin/uvicorn data_ingestion_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]