# Estágio 1: Builder - Instala dependências em um ambiente virtual
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HTTP_TIMEOUT=300
ENV POETRY_REQUESTS_TIMEOUT=300
WORKDIR /app

RUN pip install poetry==1.8.0

# Copy only needed libs (direct + transitive dependencies)
COPY libs/blu_models ./libs/blu_models
COPY libs/blu_db_connector ./libs/blu_db_connector
COPY libs/blu_context_service ./libs/blu_context_service
COPY libs/blu_supabase_client ./libs/blu_supabase_client
COPY libs/blu_auth ./libs/blu_auth
COPY libs/blu_observability_bootstrap ./libs/blu_observability_bootstrap
COPY libs/blu_llm_service ./libs/blu_llm_service
COPY libs/blu_rag_factory ./libs/blu_rag_factory
COPY libs/blu_sql_factory ./libs/blu_sql_factory
COPY libs/blu_tool_registry ./libs/blu_tool_registry
COPY libs/blu_prompt_management ./libs/blu_prompt_management
COPY libs/blu_google_suite_client ./libs/blu_google_suite_client
COPY libs/blu_parsers ./libs/blu_parsers
COPY libs/blu_elicitation_service ./libs/blu_elicitation_service
COPY libs/blu_agent_framework ./libs/blu_agent_framework
COPY libs/blu_twilio_client ./libs/blu_twilio_client

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
COPY libs/blu_models/src ./libs/blu_models/src
COPY libs/blu_db_connector/src ./libs/blu_db_connector/src
COPY libs/blu_context_service/src ./libs/blu_context_service/src
COPY libs/blu_supabase_client/src ./libs/blu_supabase_client/src
COPY libs/blu_auth/src ./libs/blu_auth/src
COPY libs/blu_observability_bootstrap/src ./libs/blu_observability_bootstrap/src
COPY libs/blu_llm_service/src ./libs/blu_llm_service/src
COPY libs/blu_rag_factory/src ./libs/blu_rag_factory/src
COPY libs/blu_sql_factory/src ./libs/blu_sql_factory/src
COPY libs/blu_tool_registry/src ./libs/blu_tool_registry/src
COPY libs/blu_prompt_management/src ./libs/blu_prompt_management/src
COPY libs/blu_google_suite_client/src ./libs/blu_google_suite_client/src
COPY libs/blu_parsers/src ./libs/blu_parsers/src
COPY libs/blu_elicitation_service/src ./libs/blu_elicitation_service/src
COPY libs/blu_agent_framework/src ./libs/blu_agent_framework/src
COPY libs/blu_twilio_client/src ./libs/blu_twilio_client/src

# Copy service source code
COPY services/tool_pool_api/src ./src

# PYTHONPATH for imports
ENV PATH="/app/services/tool_pool_api/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs/blu_models/src:/app/libs/blu_db_connector/src:/app/libs/blu_context_service/src:/app/libs/blu_supabase_client/src:/app/libs/blu_auth/src:/app/libs/blu_observability_bootstrap/src:/app/libs/blu_llm_service/src:/app/libs/blu_rag_factory/src:/app/libs/blu_sql_factory/src:/app/libs/blu_tool_registry/src:/app/libs/blu_prompt_management/src:/app/libs/blu_google_suite_client/src:/app/libs/blu_parsers/src:/app/libs/blu_elicitation_service/src:/app/libs/blu_agent_framework/src:/app/libs/blu_twilio_client/src"

EXPOSE 8000

# Use the PORT env var provided by Cloud Run (defaults to 8000)
CMD ["/bin/sh", "-c", "/app/services/tool_pool_api/.venv/bin/uvicorn tool_pool_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# Cleanup unnecessary files inside the virtualenv to reduce image size
RUN find /app/services/tool_pool_api/.venv -name "__pycache__" -type d -exec rm -rf {} + || true
RUN find /app/services/tool_pool_api/.venv -name "tests" -type d -exec rm -rf {} + || true
RUN rm -rf /app/services/tool_pool_api/.venv/lib/python3.11/site-packages/*.dist-info/*-info || true