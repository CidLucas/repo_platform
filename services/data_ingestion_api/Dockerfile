# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copy only required libs
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_supabase_client libs/vizu_supabase_client
COPY libs/vizu_auth libs/vizu_auth
COPY libs/__init__.py libs/__init__.py

# Copy service
COPY services/data_ingestion_api services/data_ingestion_api

WORKDIR /app/services/data_ingestion_api
RUN poetry install --no-root --only main

# Stage 2: Runtime
FROM python:3.11-slim AS final

WORKDIR /app/services/data_ingestion_api

# PATH and PYTHONPATH - absolute paths
ENV PATH="/app/services/data_ingestion_api/.venv/bin:$PATH" \
    PYTHONPATH="/app:/app/services/data_ingestion_api/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app/libs/vizu_supabase_client/src:/app/libs/vizu_auth/src"

# Copy .venv to same path as builder (shebangs)
COPY --from=builder /app/services/data_ingestion_api/.venv ./.venv

# Copy lib src directories
COPY --from=builder /app/libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/libs/vizu_supabase_client/src /app/libs/vizu_supabase_client/src
COPY --from=builder /app/libs/vizu_auth/src /app/libs/vizu_auth/src

# Copy service source
COPY --from=builder /app/services/data_ingestion_api/src ./src

EXPOSE 8000

CMD ["uvicorn", "data_ingestion_api.core.main:app", "--host", "0.0.0.0", "--port", "8000"]