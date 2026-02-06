# Estágio 1: Builder - Instala dependências em um ambiente virtual
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HTTP_TIMEOUT=300
ENV POETRY_REQUESTS_TIMEOUT=300
WORKDIR /app

RUN pip install poetry==1.8.0

# Copy only needed libs (direct + transitive dependencies)
COPY libs/vizu_models ./libs/vizu_models
COPY libs/vizu_db_connector ./libs/vizu_db_connector
COPY libs/vizu_context_service ./libs/vizu_context_service
COPY libs/vizu_supabase_client ./libs/vizu_supabase_client
COPY libs/vizu_auth ./libs/vizu_auth
COPY libs/vizu_observability_bootstrap ./libs/vizu_observability_bootstrap
COPY libs/vizu_llm_service ./libs/vizu_llm_service
COPY libs/vizu_qdrant_client ./libs/vizu_qdrant_client
COPY libs/vizu_rag_factory ./libs/vizu_rag_factory
COPY libs/vizu_sql_factory ./libs/vizu_sql_factory
COPY libs/vizu_tool_registry ./libs/vizu_tool_registry
COPY libs/vizu_prompt_management ./libs/vizu_prompt_management
COPY libs/vizu_google_suite_client ./libs/vizu_google_suite_client

# Copy pyproject and install deps
COPY services/tool_pool_api/pyproject.toml services/tool_pool_api/poetry.lock* ./services/tool_pool_api/

WORKDIR /app/services/tool_pool_api
RUN poetry install --no-root
RUN rm -rf /root/.cache/pip /root/.cache/pypoetry || true

# ----------------------------------------------------------------
# Estágio 2: Final - Imagem mínima de produção
FROM python:3.11-slim

WORKDIR /app

# Copy .venv to the same path it had in the builder (preserves console-script shebangs)
COPY --from=builder /app/services/tool_pool_api/.venv /app/services/tool_pool_api/.venv

# Copy only src/ folders of libs (not pyproject.toml)
COPY libs/vizu_models/src ./libs/vizu_models/src
COPY libs/vizu_db_connector/src ./libs/vizu_db_connector/src
COPY libs/vizu_context_service/src ./libs/vizu_context_service/src
COPY libs/vizu_supabase_client/src ./libs/vizu_supabase_client/src
COPY libs/vizu_auth/src ./libs/vizu_auth/src
COPY libs/vizu_observability_bootstrap/src ./libs/vizu_observability_bootstrap/src
COPY libs/vizu_llm_service/src ./libs/vizu_llm_service/src
COPY libs/vizu_qdrant_client/src ./libs/vizu_qdrant_client/src
COPY libs/vizu_rag_factory/src ./libs/vizu_rag_factory/src
COPY libs/vizu_sql_factory/src ./libs/vizu_sql_factory/src
COPY libs/vizu_tool_registry/src ./libs/vizu_tool_registry/src
COPY libs/vizu_prompt_management/src ./libs/vizu_prompt_management/src
COPY libs/vizu_google_suite_client/src ./libs/vizu_google_suite_client/src

# Copy service source code
COPY services/tool_pool_api/src ./src

# PYTHONPATH for imports
ENV PATH="/app/services/tool_pool_api/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs/vizu_models/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_context_service/src:/app/libs/vizu_supabase_client/src:/app/libs/vizu_auth/src:/app/libs/vizu_observability_bootstrap/src:/app/libs/vizu_llm_service/src:/app/libs/vizu_qdrant_client/src:/app/libs/vizu_rag_factory/src:/app/libs/vizu_sql_factory/src:/app/libs/vizu_tool_registry/src:/app/libs/vizu_prompt_management/src:/app/libs/vizu_google_suite_client/src"

EXPOSE 8000

# Use the PORT env var provided by Cloud Run (defaults to 8000)
CMD ["/bin/sh", "-c", "/app/services/tool_pool_api/.venv/bin/uvicorn tool_pool_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# Cleanup unnecessary files inside the virtualenv to reduce image size
RUN find /app/services/tool_pool_api/.venv -name "__pycache__" -type d -exec rm -rf {} + || true
RUN find /app/services/tool_pool_api/.venv -name "tests" -type d -exec rm -rf {} + || true
RUN rm -rf /app/services/tool_pool_api/.venv/lib/python3.11/site-packages/*.dist-info/*-info || true