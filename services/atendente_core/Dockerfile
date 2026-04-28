# Estágio 1: Builder - Instala as dependências
FROM --platform=linux/amd64 python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HTTP_TIMEOUT=300
ENV POETRY_REQUESTS_TIMEOUT=300
WORKDIR /app

RUN pip install poetry

# Copia libs necessárias (diretas + transitivas)
COPY libs/blu_models ./libs/blu_models
COPY libs/blu_db_connector ./libs/blu_db_connector
COPY libs/blu_supabase_client ./libs/blu_supabase_client
COPY libs/blu_context_service ./libs/blu_context_service
COPY libs/blu_auth ./libs/blu_auth
COPY libs/blu_tool_registry ./libs/blu_tool_registry
COPY libs/blu_prompt_management ./libs/blu_prompt_management
COPY libs/blu_elicitation_service ./libs/blu_elicitation_service
COPY libs/blu_observability_bootstrap ./libs/blu_observability_bootstrap
COPY libs/blu_agent_framework ./libs/blu_agent_framework
COPY libs/blu_llm_service ./libs/blu_llm_service
COPY libs/blu_hitl_service ./libs/blu_hitl_service
COPY libs/blu_sql_factory ./libs/blu_sql_factory
COPY libs/blu_twilio_client ./libs/blu_twilio_client

# Copia pyproject e instala dependências
COPY services/atendente_core/pyproject.toml services/atendente_core/poetry.lock* ./services/atendente_core/

WORKDIR /app/services/atendente_core
RUN poetry install --no-root

# ----------------------------------------------------------------
# Estágio 2: Final - Imagem mínima de produção
FROM python:3.11-slim

WORKDIR /app

# Copia .venv to the same path used during build (preserves console-script shebangs)
COPY --from=builder /app/services/atendente_core/.venv /app/services/atendente_core/.venv

# Copia apenas os src/ das libs (não o pyproject.toml)
COPY libs/blu_models/src ./libs/blu_models/src
COPY libs/blu_db_connector/src ./libs/blu_db_connector/src
COPY libs/blu_supabase_client/src ./libs/blu_supabase_client/src
COPY libs/blu_context_service/src ./libs/blu_context_service/src
COPY libs/blu_auth/src ./libs/blu_auth/src
COPY libs/blu_tool_registry/src ./libs/blu_tool_registry/src
COPY libs/blu_prompt_management/src ./libs/blu_prompt_management/src
COPY libs/blu_elicitation_service/src ./libs/blu_elicitation_service/src
COPY libs/blu_observability_bootstrap/src ./libs/blu_observability_bootstrap/src
COPY libs/blu_agent_framework/src ./libs/blu_agent_framework/src
COPY libs/blu_llm_service/src ./libs/blu_llm_service/src
COPY libs/blu_hitl_service/src ./libs/blu_hitl_service/src
COPY libs/blu_sql_factory/src ./libs/blu_sql_factory/src
COPY libs/blu_twilio_client/src ./libs/blu_twilio_client/src

# Copia código fonte do serviço
COPY services/atendente_core/src ./src

# PYTHONPATH para imports
ENV PATH="/app/services/atendente_core/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs/blu_models/src:/app/libs/blu_db_connector/src:/app/libs/blu_supabase_client/src:/app/libs/blu_context_service/src:/app/libs/blu_auth/src:/app/libs/blu_tool_registry/src:/app/libs/blu_prompt_management/src:/app/libs/blu_elicitation_service/src:/app/libs/blu_observability_bootstrap/src:/app/libs/blu_agent_framework/src:/app/libs/blu_llm_service/src:/app/libs/blu_hitl_service/src:/app/libs/blu_sql_factory/src:/app/libs/blu_twilio_client/src"

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/services/atendente_core/.venv/bin/python -m uvicorn atendente_core.main:app --host 0.0.0.0 --port ${PORT:-8000}"]