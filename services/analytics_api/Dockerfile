# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copy only required libs
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_auth libs/vizu_auth

# Copy service
COPY services/analytics_api services/analytics_api

WORKDIR /app/services/analytics_api
RUN poetry install --no-root

# Stage 2: Runtime
FROM python:3.11-slim AS final

WORKDIR /app/services/analytics_api

# PATH and PYTHONPATH - absolute paths
ENV PATH="/app/services/analytics_api/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/analytics_api/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app/libs/vizu_auth/src"

# Copy .venv to same path as builder (shebangs)
COPY --from=builder /app/services/analytics_api/.venv ./.venv

# Copy lib src directories
COPY --from=builder /app/libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/libs/vizu_auth/src /app/libs/vizu_auth/src

# Copy service source
COPY --from=builder /app/services/analytics_api/src ./src

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/services/analytics_api/.venv/bin/uvicorn analytics_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]