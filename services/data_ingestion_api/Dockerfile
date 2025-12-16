# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copy only required libs
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models

# Copy service
COPY services/data_ingestion_api services/data_ingestion_api

WORKDIR /app/services/data_ingestion_api
RUN poetry install --no-root --only main

# Stage 2: Runtime
FROM python:3.11-slim AS final

WORKDIR /app/services/data_ingestion_api

# PATH and PYTHONPATH - absolute paths
ENV PATH="/app/services/data_ingestion_api/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/data_ingestion_api/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src"

# Copy .venv to same path as builder (shebangs)
COPY --from=builder /app/services/data_ingestion_api/.venv ./.venv

# Copy lib src directories
COPY --from=builder /app/libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src

# Copy service source
COPY --from=builder /app/services/data_ingestion_api/src ./src

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/services/data_ingestion_api/.venv/bin/uvicorn data_ingestion_api.core.main:app --host 0.0.0.0 --port ${PORT:-8000}"]