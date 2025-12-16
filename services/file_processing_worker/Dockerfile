# Stage 1: Builder - Instala as dependências
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copy only the libs actually needed by file_processing_worker
COPY libs/vizu_observability_bootstrap libs/vizu_observability_bootstrap
COPY libs/vizu_models libs/vizu_models
COPY libs/vizu_qdrant_client libs/vizu_qdrant_client
COPY libs/vizu_llm_service libs/vizu_llm_service

# Copia o serviço
COPY services/file_processing_worker services/file_processing_worker

# Instala as dependências no .venv local do projeto
WORKDIR /app/services/file_processing_worker
RUN poetry install --no-root

# Stage 2: Runtime - Imagem final otimizada
FROM python:3.11-slim as final

# WORKDIR must match builder path so shebangs in .venv work correctly
WORKDIR /app/services/file_processing_worker

# PATH and PYTHONPATH - use absolute paths for reliability
ENV PATH="/app/services/file_processing_worker/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/file_processing_worker/src:/app/libs/vizu_observability_bootstrap/src:/app/libs/vizu_models/src:/app/libs/vizu_qdrant_client/src:/app/libs/vizu_llm_service/src"

# Copy .venv to SAME path as builder (shebangs reference this absolute path)
COPY --from=builder /app/services/file_processing_worker/.venv ./.venv

# Copy lib src directories to /app/libs (matching PYTHONPATH)
COPY --from=builder /app/libs/vizu_observability_bootstrap/src /app/libs/vizu_observability_bootstrap/src
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/libs/vizu_qdrant_client/src /app/libs/vizu_qdrant_client/src
COPY --from=builder /app/libs/vizu_llm_service/src /app/libs/vizu_llm_service/src

# Copy service source code
COPY --from=builder /app/services/file_processing_worker/src ./src

EXPOSE 8000

# Use the PORT provided by Cloud Run and the venv-installed uvicorn.
CMD ["/bin/sh", "-c", "/app/services/file_processing_worker/.venv/bin/uvicorn file_processing_worker.main:app --host 0.0.0.0 --port ${PORT:-8000}"]