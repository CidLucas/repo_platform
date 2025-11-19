# Estágio 1: Build da Imagem Base
FROM python:3.11-slim as builder

# Instala o Poetry
WORKDIR /app
RUN pip install poetry
ENV POETRY_VIRTUALENVS_PATH=/app/services/data_ingestion_api/.venv
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Copia os arquivos necessários para o contexto do build
COPY libs /app/libs
COPY services/data_ingestion_api /app/services/data_ingestion_api

# Muda o WORKDIR para a pasta do serviço antes de instalar as dependências
WORKDIR /app/services/data_ingestion_api
RUN poetry lock # Generate poetry.lock
RUN poetry install --no-root --only main

# Estágio 2: Imagem Final de Produção (Slim)
FROM python:3.11-slim as production

# Define variáveis de ambiente Vizu
ENV PYTHONUNBUFFERED 1
ENV VIZU_SERVICE_NAME=data-ingestion-api
ENV VIZU_ENVIRONMENT=production

# Copia os pacotes instalados e o código-fonte
WORKDIR /app
ENV PATH="/app/services/data_ingestion_api/.venv/bin:$PATH"
COPY --from=builder /app/services/data_ingestion_api/.venv /app/services/data_ingestion_api/.venv
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY services/data_ingestion_api/src/ /app/src/

# O ponto crítico: O comando deve apontar para o novo pacote raiz
# Estrutura: [pacote_raiz].[subpasta_core].[módulo]:[instância_fastapi]
CMD ["uvicorn", "data_ingestion_api.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Opcional: Expõe a porta
EXPOSE 8000