# Estágio 1: Builder - Instala dependências em um ambiente virtual
FROM python:3.11-slim as builder

# Instala o Poetry
RUN pip install poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app

# 1. COPIE as 'libs' primeiro. (Camada de cache para dependências)
# Copiamos todas as libs que o tool_pool_api vai precisar
COPY ./libs/vizu_llm_service ./libs/vizu_llm_service
COPY ./libs/vizu_qdrant_client ./libs/vizu_qdrant_client
COPY ./libs/vizu_context_service ./libs/vizu_context_service
COPY ./libs/vizu_rag_factory ./libs/vizu_rag_factory
COPY ./libs/vizu_sql_factory ./libs/vizu_sql_factory
COPY ./libs/vizu_db_connector ./libs/vizu_db_connector
COPY ./libs/vizu_models ./libs/vizu_models
COPY ./libs/vizu_auth ./libs/vizu_auth
COPY ./libs/vizu_supabase_client ./libs/vizu_supabase_client
COPY ./libs/vizu_google_suite_client ./libs/vizu_google_suite_client

# 2. COPIE os arquivos de projeto para sua estrutura de pastas espelhada.
COPY ./services/tool_pool_api/pyproject.toml ./services/tool_pool_api/poetry.lock* ./services/tool_pool_api/

# 3. MUDE o WORKDIR para o diretório do serviço.
WORKDIR /app/services/tool_pool_api

# 4. INSTALE as dependências (sem a 'root', apenas dependências)
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    poetry install --no-root

# Estágio 2: Final - A imagem de produção limpa
FROM python:3.11-slim

# Define o WORKDIR principal da aplicação (dentro do serviço)
WORKDIR /app/services/tool_pool_api

# 5. COPIE o .venv do local exato onde foi criado no builder.
COPY --from=builder /app/services/tool_pool_api/.venv ./.venv

# 6. COPIE o código fonte do serviço
COPY ./services/tool_pool_api/src ./src

# 7. COPIE o código fonte das 'libs' (Necessário para execução)
WORKDIR /app
COPY ./libs/vizu_context_service/src ./libs/vizu_context_service/src
COPY ./libs/vizu_rag_factory/src ./libs/vizu_rag_factory/src
COPY ./libs/vizu_sql_factory/src ./libs/vizu_sql_factory/src
COPY ./libs/vizu_db_connector/src ./libs/vizu_db_connector/src
COPY ./libs/vizu_models/src ./libs/vizu_models/src
COPY ./libs/vizu_llm_service/src ./libs/vizu_llm_service/src
COPY ./libs/vizu_qdrant_client/src ./libs/vizu_qdrant_client/src
COPY ./libs/vizu_auth/src ./libs/vizu_auth/src
COPY ./libs/vizu_supabase_client/src ./libs/vizu_supabase_client/src
COPY ./libs/vizu_google_suite_client/src ./libs/vizu_google_suite_client/src

# 8. Define o WORKDIR final de volta para o serviço
WORKDIR /app/services/tool_pool_api

# 9. Ativa o .venv e define o comando de execução
# O main.py chamará mcp.run()
CMD ["/app/services/tool_pool_api/.venv/bin/python", "-m", "tool_pool_api.main"]