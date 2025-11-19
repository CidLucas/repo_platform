# Padrão Vizu: Baseado no Dockerfile do file_processing_worker

# --- ESTÁGIO 1: BUILDER ---
FROM python:3.11-slim as builder
RUN pip install poetry

# New strategy for virtual environment
ENV VIRTUAL_ENV=/opt/pysetup/.venv
ENV PATH="/opt/pysetup/.venv/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app
# Copy all libs to /app/libs
COPY ./libs ./libs

WORKDIR /app/services/embedding_service # Change WORKDIR to the service directory
COPY ./services/embedding_service/pyproject.toml ./services/embedding_service/poetry.lock* ./
RUN python -m venv $VIRTUAL_ENV
RUN poetry install --no-root --sync --no-interaction


# --- ESTÁGIO 2: FINAL (PRODUÇÃO) ---
FROM python:3.11-slim as final

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs"

COPY --from=builder /opt/pysetup/.venv /opt/pysetup/.venv
ENV PATH="/opt/pysetup/.venv/bin:$PATH"

COPY --from=builder /app/libs ./libs
COPY --chown=appuser:appuser ./services/embedding_service/src/embedding_service ./embedding_service

USER appuser
# Expõe a porta que definimos para este serviço
EXPOSE 11435

# Aponta o CMD para o módulo 'embedding_service' (que copiamos acima)
# e seu arquivo 'main', variável 'app', na porta 11435.
CMD ["/opt/pysetup/.venv/bin/python", "-m", "uvicorn", "embedding_service.main:app", "--host", "0.0.0.0", "--port", "11435"]