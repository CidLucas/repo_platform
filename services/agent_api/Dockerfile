FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HTTP_TIMEOUT=300
WORKDIR /app

RUN pip install poetry==1.8.0

# Copy internal libs (needed for path-dependency resolution during install)
COPY libs/blu_auth ./libs/blu_auth
COPY libs/blu_models ./libs/blu_models
COPY libs/blu_agent_framework ./libs/blu_agent_framework
COPY libs/blu_prompt_management ./libs/blu_prompt_management
COPY libs/blu_llm_service ./libs/blu_llm_service
COPY libs/blu_tool_registry ./libs/blu_tool_registry
COPY libs/blu_context_service ./libs/blu_context_service
COPY libs/blu_db_connector ./libs/blu_db_connector
COPY libs/blu_supabase_client ./libs/blu_supabase_client
COPY libs/blu_parsers ./libs/blu_parsers
COPY libs/blu_rag_factory ./libs/blu_rag_factory
COPY libs/blu_hitl_service ./libs/blu_hitl_service
COPY libs/blu_elicitation_service ./libs/blu_elicitation_service
COPY libs/blu_sql_factory ./libs/blu_sql_factory
COPY libs/blu_observability_bootstrap ./libs/blu_observability_bootstrap

# Copy service manifest and install deps into .venv
COPY services/agent_api/pyproject.toml services/agent_api/poetry.lock* ./services/agent_api/

WORKDIR /app/services/agent_api
RUN poetry install --no-root --without dev
RUN rm -rf /root/.cache/pip /root/.cache/pypoetry || true

# ----------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /app/services/agent_api/.venv /app/services/agent_api/.venv

# Copy lib sources only (no pyproject.toml needed at runtime)
COPY libs/blu_auth/src ./libs/blu_auth/src
COPY libs/blu_models/src ./libs/blu_models/src
COPY libs/blu_agent_framework/src ./libs/blu_agent_framework/src
COPY libs/blu_prompt_management/src ./libs/blu_prompt_management/src
COPY libs/blu_llm_service/src ./libs/blu_llm_service/src
COPY libs/blu_tool_registry/src ./libs/blu_tool_registry/src
COPY libs/blu_context_service/src ./libs/blu_context_service/src
COPY libs/blu_db_connector/src ./libs/blu_db_connector/src
COPY libs/blu_supabase_client/src ./libs/blu_supabase_client/src
COPY libs/blu_parsers/src ./libs/blu_parsers/src
COPY libs/blu_rag_factory/src ./libs/blu_rag_factory/src
COPY libs/blu_hitl_service/src ./libs/blu_hitl_service/src
COPY libs/blu_elicitation_service/src ./libs/blu_elicitation_service/src
COPY libs/blu_sql_factory/src ./libs/blu_sql_factory/src
COPY libs/blu_observability_bootstrap/src ./libs/blu_observability_bootstrap/src

# Copy service source
COPY services/agent_api/src ./src

ENV PATH="/app/services/agent_api/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs/blu_auth/src:/app/libs/blu_models/src:/app/libs/blu_agent_framework/src:/app/libs/blu_prompt_management/src:/app/libs/blu_llm_service/src:/app/libs/blu_tool_registry/src:/app/libs/blu_context_service/src:/app/libs/blu_db_connector/src:/app/libs/blu_supabase_client/src:/app/libs/blu_parsers/src:/app/libs/blu_rag_factory/src:/app/libs/blu_hitl_service/src:/app/libs/blu_elicitation_service/src:/app/libs/blu_sql_factory/src:/app/libs/blu_observability_bootstrap/src"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/services/agent_api/.venv/bin/uvicorn agent_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
