# Stage 1: Builder - Instala dependências
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copia as libs (path dependencies)
COPY libs/vizu_db_connector libs/vizu_db_connector
COPY libs/vizu_models libs/vizu_models

# Copia o serviço
COPY services/data_ingestion_api services/data_ingestion_api

# Instala as dependências no .venv local do projeto
WORKDIR /app/services/data_ingestion_api
RUN poetry lock && poetry install --no-root --only main

# Stage 2: Runtime - Imagem final otimizada
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    VIZU_SERVICE_NAME=data-ingestion-api \
    VIZU_ENVIRONMENT=production

WORKDIR /app

# Copia apenas o .venv (contém todas as dependências)
COPY --from=builder /app/services/data_ingestion_api/.venv ./services/data_ingestion_api/.venv

# Copia apenas o src/ das libs (sem pyproject.toml, poetry.lock, tests, etc)
COPY --from=builder /app/libs/vizu_db_connector/src ./libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_models/src ./libs/vizu_models/src

# Copia o código-fonte do serviço
COPY --from=builder /app/services/data_ingestion_api/src ./src

# Configura PATH e PYTHONPATH
ENV PATH="/app/services/data_ingestion_api/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src"

EXPOSE 8000

# Use the PORT env var provided by Cloud Run (defaults to 8000)
CMD ["/bin/sh", "-c", "uvicorn data_ingestion_api.core.main:app --host 0.0.0.0 --port ${PORT:-8000}"]