# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copy only required libs
COPY libs/vizu_observability_bootstrap libs/vizu_observability_bootstrap
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_supabase_client libs/vizu_supabase_client

# Copy service
COPY services/file_upload_api services/file_upload_api

WORKDIR /app/services/file_upload_api
RUN poetry install --no-root

# Stage 2: Runtime
FROM python:3.11-slim AS final

WORKDIR /app/services/file_upload_api

# PATH and PYTHONPATH - absolute paths
ENV PATH="/app/services/file_upload_api/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/file_upload_api/src:/app/libs/vizu_observability_bootstrap/src:/app/libs/vizu_models/src:/app/libs/vizu_supabase_client/src"

# Copy .venv to same path as builder (shebangs)
COPY --from=builder /app/services/file_upload_api/.venv ./.venv

# Copy lib src directories
COPY --from=builder /app/libs/vizu_observability_bootstrap/src /app/libs/vizu_observability_bootstrap/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/libs/vizu_supabase_client/src /app/libs/vizu_supabase_client/src

# Copy service source
COPY --from=builder /app/services/file_upload_api/src ./src

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/services/file_upload_api/.venv/bin/uvicorn file_upload_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]