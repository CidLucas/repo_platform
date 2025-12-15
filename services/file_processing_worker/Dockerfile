# Stage 1: Builder - Instala as dependências
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copia as libs (path dependencies)
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

RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

ENV PYTHONPATH="/home/appuser/app/src:/home/appuser/app/libs/vizu_observability_bootstrap/src:/home/appuser/app/libs/vizu_models/src:/home/appuser/app/libs/vizu_qdrant_client/src:/home/appuser/app/libs/vizu_llm_service/src" \
    PATH="/home/appuser/app/.venv/bin:$PATH"

# Copia apenas o .venv (contém todas as dependências)
COPY --from=builder --chown=appuser:appuser /app/services/file_processing_worker/.venv ./.venv

# Copia apenas o src/ das libs (sem pyproject.toml, poetry.lock, tests, etc)
COPY --from=builder --chown=appuser:appuser /app/libs/vizu_observability_bootstrap/src ./libs/vizu_observability_bootstrap/src
COPY --from=builder --chown=appuser:appuser /app/libs/vizu_models/src ./libs/vizu_models/src
COPY --from=builder --chown=appuser:appuser /app/libs/vizu_qdrant_client/src ./libs/vizu_qdrant_client/src
COPY --from=builder --chown=appuser:appuser /app/libs/vizu_llm_service/src ./libs/vizu_llm_service/src

# Copia o código-fonte do worker
COPY --from=builder --chown=appuser:appuser /app/services/file_processing_worker/src ./src

USER appuser
EXPOSE 8000

# Use the PORT provided by Cloud Run and the venv-installed uvicorn.
# Running via sh -c allows shell expansion of ${PORT:-8000}.
CMD ["sh", "-c", "/home/appuser/app/.venv/bin/uvicorn file_processing_worker.main:app --host 0.0.0.0 --port ${PORT:-8000}"]