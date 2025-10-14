# Estágio 1: Builder - Instala as dependências (padrão Vizu)
FROM --platform=linux/amd64 python:3.11-slim as builder

# Configura o Poetry para criar o .venv dentro do projeto
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry

# Copia os arquivos de configuração e as libs primeiro para otimizar o cache
COPY libs ./libs
COPY services/clients_api/pyproject.toml services/clients_api/poetry.lock ./services/clients_api/

# Instala as dependências
WORKDIR /app/services/clients_api
# ---- CORREÇÃO FINAL AQUI ----
# Removemos a flag '--without dev' porque o pyproject.toml deste serviço não tem um grupo [dev]
RUN poetry install --no-root

# ----------------------------------------------------------------
# Estágio 2: Final - A imagem de produção
FROM python:3.11-slim

WORKDIR /app

# Copia o ambiente virtual com as dependências do estágio 'builder'
COPY --from=builder /app/services/clients_api/.venv ./.venv

# Copia as bibliotecas compartilhadas
COPY --from=builder /app/libs ./libs

# Copia o código-fonte da aplicação
COPY services/clients_api/src ./src


# Configura o PATH para encontrar os executáveis do .venv e o PYTHONPATH para os imports
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs"

EXPOSE 8000

# Comando final, usando o caminho absoluto para o python e executando uvicorn como módulo
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "clients_api.main:app", "--host", "0.0.0.0", "--port", "8000"]