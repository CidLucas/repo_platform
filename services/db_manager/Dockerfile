# services/db_manager/Dockerfile
# VERSÃO DE DEPURAÇÃO

# --- 1. Builder Stage ---
FROM python:3.11-slim as builder

RUN pip install poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app

COPY ./libs ./libs
COPY ./services/db_manager/pyproject.toml ./services/db_manager/poetry.lock* ./services/db_manager/

WORKDIR /app/services/db_manager
RUN poetry install --no-root

# --- PASSO DE DEPURAÇÃO ---
# Vamos listar o conteúdo do diretório bin do venv para ver se 'alembic' está lá.
RUN ls -la /app/services/db_manager/.venv/bin


# --- 2. Final Stage ---
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/services/db_manager/.venv ./.venv
COPY ./services/db_manager/src/db_manager ./db_manager
COPY ./services/db_manager/alembic ./alembic
COPY ./services/db_manager/alembic.ini ./alembic.ini
COPY ./libs/vizu_db_connector ./libs/vizu_db_connector
COPY ./libs/vizu_shared_models ./libs/vizu_shared_models
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "-m", "db_manager.main"]
CMD ["migrate"]