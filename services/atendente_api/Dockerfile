# 1. Estágio de Build: Instala o Poetry e as dependências
FROM python:3.11-slim as builder

# Define o diretório de trabalho
WORKDIR /app

# Instala o Poetry
RUN pip install poetry

# Copia os arquivos de configuração do Poetry
COPY pyproject.toml poetry.lock ./

# Instala as dependências do projeto, incluindo as de desenvolvimento para testes
# A flag --no-root impede que o próprio pacote seja instalado neste estágio
RUN poetry install --no-root

# --- Monorepo: Copia as bibliotecas compartilhadas ---
# Copia o código-fonte das nossas bibliotecas locais para a imagem
COPY ../../libs/vizu_shared_models /app/libs/vizu_shared_models
COPY ../../libs/vizu_db_connector /app/libs/vizu_db_connector
COPY ../../libs/vizu_qdrant_client /app/libs/vizu_qdrant_client
COPY ../../libs/vizu_llm_service /app/libs/vizu_llm_service

# Copia o código-fonte da aplicação
COPY src/atendente_api ./src/atendente_api

# 2. Estágio de Produção: Cria a imagem final e enxuta
FROM python:3.11-slim

WORKDIR /app

# Copia o ambiente virtual com as dependências do estágio de build
COPY --from=builder /root/.cache/pypoetry/virtualenvs ./.venv
# Copia o código-fonte da aplicação e das bibliotecas
COPY --from=builder /app/src ./src
COPY --from=builder /app/libs ./libs

# Ativa o ambiente virtual para os comandos subsequentes
ENV PATH="/app/.venv/bin:$PATH"

# Expõe a porta em que o FastAPI irá rodar
EXPOSE 8000

# Comando para iniciar a aplicação usando Uvicorn
CMD ["uvicorn", "atendente_api.main:app", "--host", "0.0.0.0", "--port", "8000"]