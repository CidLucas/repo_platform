# Estágio 1: Builder - Responsável por instalar as dependências
FROM python:3.11-slim AS builder

WORKDIR /app

# Instala as dependências diretamente com pip (mais confiável que Poetry em Docker)
RUN pip install --no-cache-dir \
    streamlit>=1.30.0 \
    pandas>=2.1.0 \
    httpx>=0.26.0 \
    pydantic-settings>=2.1.0 \
    loguru>=0.7.2 \
    python-dotenv>=1.0.0 \
    requests>=2.32.0 \
    sqlmodel>=0.0.22 \
    psycopg2-binary>=2.9.7 \
    alembic>=1.12.0

# Estágio 2: Final - Imagem de execução
FROM python:3.11-slim

WORKDIR /app

# Copia os pacotes instalados do builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia o código fonte da aplicação e libs
COPY ./ferramentas/evaluation_suite/src ./src
COPY ./libs ./libs

# Configura o PYTHONPATH
ENV PYTHONPATH="/app/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src"

# Verifica que streamlit está disponível
RUN streamlit --version

# Comando de execução
CMD ["streamlit", "run", "/app/src/evaluation_suite/main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]