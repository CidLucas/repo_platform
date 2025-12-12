# Stage 1: Build - Instala dependências
FROM python:3.11-slim as builder

WORKDIR /app

# Instala Poetry e build dependencies (necessário para compilar packages com C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip poetry

# Configure Poetry to not use virtualenvs (since we're in a container)
ENV POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copia todos os arquivos de manifesto das libs (necessário para path dependencies)
COPY libs/vizu_db_connector/pyproject.toml libs/vizu_db_connector/poetry.lock* \
    /app/libs/vizu_db_connector/
COPY libs/vizu_models/pyproject.toml libs/vizu_models/poetry.lock* \
    /app/libs/vizu_models/
COPY libs/vizu_shared_utils/pyproject.toml libs/vizu_shared_utils/poetry.lock* \
    /app/libs/vizu_shared_utils/

# Copia os serviços relacionados
COPY services/data_ingestion_api/pyproject.toml services/data_ingestion_api/poetry.lock* \
    /app/services/data_ingestion_api/
COPY services/data_ingestion_worker/pyproject.toml services/data_ingestion_worker/poetry.lock* \
    /app/services/data_ingestion_worker/

# Copia o código-fonte das libs (necessário para instalar com develop=true)
COPY libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY libs/vizu_models/src /app/libs/vizu_models/src
COPY libs/vizu_shared_utils/src /app/libs/vizu_shared_utils/src
COPY services/data_ingestion_api/src /app/services/data_ingestion_api/src

# Instala as dependências (incluindo path dependencies)
WORKDIR /app/services/data_ingestion_worker
RUN poetry install --only main --no-root


# Stage 2: Produção - Imagem final Serverless
FROM python:3.11-slim as production

WORKDIR /app

# Copia dependências instaladas e o código-fonte
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages/
COPY services/data_ingestion_worker/src /app/src/
COPY services/data_ingestion_api/src /app/services/data_ingestion_api/src/

# Define o PATH para que o Python encontre os pacotes do monorepo
ENV PYTHONPATH=/app/src:/app/services/data_ingestion_api/src

# Note: This service is designed for Cloud Functions (PubSub trigger)
# Entry Point: 'worker_function.pubsub_ingestion_worker'
# For Cloud Run, you can use a wrapper or adapt as needed
CMD ["python", "-m", "data_ingestion_worker.core.worker_function"]
