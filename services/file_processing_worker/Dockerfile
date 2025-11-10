# Padrão Vizu: Baseado no Dockerfile da clientes_finais_api

# --- ESTÁGIO 1: BUILDER ---
FROM python:3.11-slim as builder

WORKDIR /app
RUN pip install poetry
COPY . .

# Aponta para o diretório do nosso novo serviço
WORKDIR /app/services/file_processing_worker
RUN poetry install --no-root --no-dev

# --- ESTÁGIO 2: FINAL (PRODUÇÃO) ---
FROM python:3.11-slim as final

RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs"
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Copia o .venv do worker
COPY --from=builder --chown=appuser:appuser /app/services/file_processing_worker/.venv ./.venv
# Copia as libs (igual)
COPY --from=builder --chown=appuser:appuser /app/libs ./libs
# Copia o código-fonte do worker
COPY --chown=appuser:appuser ./services/file_processing_worker/src/file_processing_worker ./file_processing_worker

USER appuser
EXPOSE 8000

# Aponta o CMD para o módulo do worker
CMD ["/home/appuser/app/.venv/bin/python", "-m", "uvicorn", "file_processing_worker.main:app", "--host", "0.0.0.0", "--port", "8000"]