# services/migration_runner/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema necessárias para compilar psycopg2 e outras libs
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala poetry e configura para NÃO criar virtualenvs (Instala no sistema global)
RUN pip install poetry && \
    poetry config virtualenvs.create false

# Copia todo o diretório de libs para contexto
COPY ./libs ./libs

# 1. Instala Vizu Models (Isso garante que sqlmodel e pydantic sejam instalados globalmente)
WORKDIR /app/libs/vizu_models
RUN poetry install --no-root --only main

# 2. Instala Shared Utils
WORKDIR /app/libs/vizu_shared_utils
RUN poetry install --no-root --only main

# 3. Instala DB Connector (Alembic e Drivers)
WORKDIR /app/libs/vizu_db_connector
# A flag --no-interaction evita que o poetry trave perguntando coisas
RUN poetry install --no-root --only main

# Copia o script principal e configurações do Alembic
WORKDIR /app
COPY ./services/migration_runner/main.py .
# Garante que a pasta alembic e o .ini estejam no WORKDIR esperado pelo script
COPY ./libs/vizu_db_connector/alembic ./alembic
COPY ./libs/vizu_db_connector/alembic.ini .

# Define PYTHONPATH para garantir que o Python ache os módulos nas pastas libs
ENV PYTHONPATH=/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src:/app/libs/vizu_shared_utils/src

# Entrypoint direto com python (sem poetry run, pois instalamos globalmente)
ENTRYPOINT ["python", "main.py"]