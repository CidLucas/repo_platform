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
COPY libs/blu_agent_framework ./libs/blu_agent_framework
COPY libs/blu_prompt_management ./libs/blu_prompt_management
COPY libs/blu_llm_service ./libs/blu_llm_service
COPY libs/blu_tool_registry ./libs/blu_tool_registry
COPY libs/blu_rag_factory ./libs/blu_rag_factory
COPY libs/blu_auth ./libs/blu_auth
COPY libs/blu_context_service ./libs/blu_context_service
COPY libs/blu_db_connector ./libs/blu_db_connector
COPY libs/blu_supabase_client ./libs/blu_supabase_client
COPY libs/blu_observability_bootstrap ./libs/blu_observability_bootstrap
COPY libs/blu_sql_factory ./libs/blu_sql_factory
COPY libs/blu_parsers ./libs/blu_parsers

# Copy pyproject and install deps
COPY services/standalone_agent_api/pyproject.toml services/standalone_agent_api/poetry.lock* ./services/standalone_agent_api/

WORKDIR /app/services/standalone_agent_api
RUN poetry lock
RUN poetry install --no-root
RUN rm -rf /root/.cache/pip /root/.cache/pypoetry || true

# ----------------------------------------------------------------
# Estágio 2: Final - Imagem mínima de produção
FROM python:3.11-slim

WORKDIR /app

# Copy .venv to the same path it had in the builder
COPY --from=builder /app/services/standalone_agent_api/.venv /app/services/standalone_agent_api/.venv

# Copy only src/ folders of libs (not pyproject.toml)
COPY libs/blu_models/src ./libs/blu_models/src
COPY libs/blu_agent_framework/src ./libs/blu_agent_framework/src
COPY libs/blu_prompt_management/src ./libs/blu_prompt_management/src
COPY libs/blu_llm_service/src ./libs/blu_llm_service/src
COPY libs/blu_tool_registry/src ./libs/blu_tool_registry/src
COPY libs/blu_rag_factory/src ./libs/blu_rag_factory/src
COPY libs/blu_auth/src ./libs/blu_auth/src
COPY libs/blu_context_service/src ./libs/blu_context_service/src
COPY libs/blu_db_connector/src ./libs/blu_db_connector/src
COPY libs/blu_supabase_client/src ./libs/blu_supabase_client/src
COPY libs/blu_observability_bootstrap/src ./libs/blu_observability_bootstrap/src
COPY libs/blu_sql_factory/src ./libs/blu_sql_factory/src
COPY libs/blu_parsers/src ./libs/blu_parsers/src

# Copy service source code
COPY services/standalone_agent_api/src ./src

# PYTHONPATH for imports
ENV PATH="/app/services/standalone_agent_api/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run service
EXPOSE 8000
CMD ["uvicorn", "standalone_agent_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
