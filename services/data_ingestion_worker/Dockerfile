# Stage 1: Build - Instala dependências
FROM python:3.11-slim as builder

WORKDIR /app

# Instala Poetry e dependências (Monorepo-aware)
RUN pip install poetry

COPY services/data_ingestion_api/pyproject.toml services/data_ingestion_api/poetry.lock \
    /app/services/data_ingestion_api/
COPY services/data_ingestion_worker/pyproject.toml services/data_ingestion_worker/poetry.lock \
    /app/services/data_ingestion_worker/

# Instala as dependências (incluindo o link para o serviço vizinho)
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
