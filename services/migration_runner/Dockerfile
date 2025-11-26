# services/migration_runner/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy the entire libs directory first
COPY ./libs ./libs

# Install dependencies
WORKDIR /app/libs/vizu_db_connector
RUN poetry install --no-root

WORKDIR /app/libs/vizu_models
RUN poetry install --no-root

WORKDIR /app/libs/vizu_shared_utils
RUN poetry install --no-root

# Copy the rest of the files
WORKDIR /app
COPY ./services/migration_runner/main.py .
COPY ./libs/vizu_db_connector/alembic ./alembic
COPY ./libs/vizu_db_connector/alembic.ini .

ENV PYTHONPATH /app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app/libs/vizu_shared_utils/src

WORKDIR /app/libs/vizu_db_connector
ENTRYPOINT ["poetry", "run", "python", "/app/main.py"]
