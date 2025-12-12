# Stage 1: Build - Instala dependências
FROM python:3.11-slim as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.0

# Configure Poetry to use project-local virtualenvs
ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# Copy all required libs with source code (path dependencies need full source)
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_shared_utils libs/vizu_shared_utils

# Copy related services with full source
COPY services/data_ingestion_api services/data_ingestion_api
COPY services/data_ingestion_worker services/data_ingestion_worker

# Install dependencies to project-local .venv
WORKDIR /app/services/data_ingestion_worker
RUN poetry install --no-root

# Stage 2: Runtime - Imagem final Serverless
FROM python:3.11-slim as production

WORKDIR /app/services/data_ingestion_worker

# Copy .venv from builder (contains all dependencies)
COPY --from=builder /app/services/data_ingestion_worker/.venv ./.venv

# Copy lib source code for runtime path resolution
COPY --from=builder /app/libs /app/libs

# Copy service source code
COPY --from=builder /app/services/data_ingestion_worker/src ./src
COPY --from=builder /app/services/data_ingestion_api/src /app/services/data_ingestion_api/src

# Set up Python path to find all dependencies
ENV PATH="/app/services/data_ingestion_worker/.venv/bin:$PATH" \
    PYTHONPATH="src:../../libs/vizu_db_connector/src:../../libs/vizu_models/src:../../libs/vizu_shared_utils/src:/app/services/data_ingestion_api/src"

# Note: This service is designed for Cloud Functions (PubSub trigger)
# Entry Point: 'worker_function.pubsub_ingestion_worker'
# For Cloud Run, you can use a wrapper or adapt as needed
CMD ["python", "-m", "data_ingestion_worker.core.worker_function"]
