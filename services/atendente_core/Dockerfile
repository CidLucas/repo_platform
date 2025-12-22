# Estágio 1: Builder - Instala as dependências
FROM --platform=linux/amd64 python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HTTP_TIMEOUT=300
ENV POETRY_REQUESTS_TIMEOUT=300
WORKDIR /app

RUN pip install poetry

# Copia libs necessárias (diretas + transitivas)
COPY libs/vizu_models ./libs/vizu_models
COPY libs/vizu_db_connector ./libs/vizu_db_connector
COPY libs/vizu_supabase_client ./libs/vizu_supabase_client
COPY libs/vizu_context_service ./libs/vizu_context_service
COPY libs/vizu_auth ./libs/vizu_auth
COPY libs/vizu_tool_registry ./libs/vizu_tool_registry
COPY libs/vizu_prompt_management ./libs/vizu_prompt_management
COPY libs/vizu_elicitation_service ./libs/vizu_elicitation_service
COPY libs/vizu_observability_bootstrap ./libs/vizu_observability_bootstrap
COPY libs/vizu_agent_framework ./libs/vizu_agent_framework
COPY libs/vizu_llm_service ./libs/vizu_llm_service
COPY libs/vizu_hitl_service ./libs/vizu_hitl_service
COPY libs/vizu_sql_factory ./libs/vizu_sql_factory
COPY libs/vizu_twilio_client ./libs/vizu_twilio_client

# Copia pyproject e instala dependências
COPY services/atendente_core/pyproject.toml services/atendente_core/poetry.lock* ./services/atendente_core/

WORKDIR /app/services/atendente_core
RUN poetry lock && poetry install --no-root

# ----------------------------------------------------------------
# Estágio 2: Final - Imagem mínima de produção
FROM python:3.11-slim

WORKDIR /app

# Copia .venv to the same path used during build (preserves console-script shebangs)
COPY --from=builder /app/services/atendente_core/.venv /app/services/atendente_core/.venv

# Copia apenas os src/ das libs (não o pyproject.toml)
COPY libs/vizu_models/src ./libs/vizu_models/src
COPY libs/vizu_db_connector/src ./libs/vizu_db_connector/src
COPY libs/vizu_supabase_client/src ./libs/vizu_supabase_client/src
COPY libs/vizu_context_service/src ./libs/vizu_context_service/src
COPY libs/vizu_auth/src ./libs/vizu_auth/src
COPY libs/vizu_tool_registry/src ./libs/vizu_tool_registry/src
COPY libs/vizu_prompt_management/src ./libs/vizu_prompt_management/src
COPY libs/vizu_elicitation_service/src ./libs/vizu_elicitation_service/src
COPY libs/vizu_observability_bootstrap/src ./libs/vizu_observability_bootstrap/src
COPY libs/vizu_agent_framework/src ./libs/vizu_agent_framework/src
COPY libs/vizu_llm_service/src ./libs/vizu_llm_service/src
COPY libs/vizu_hitl_service/src ./libs/vizu_hitl_service/src
COPY libs/vizu_sql_factory/src ./libs/vizu_sql_factory/src
COPY libs/vizu_twilio_client/src ./libs/vizu_twilio_client/src
# Copia ferramentas de desenvolvimento (seeds, etc) - needed for batch runs
COPY ferramentas ./ferramentas
COPY scripts ./scripts

# Copia código fonte do serviço
COPY services/atendente_core/src ./src

# PYTHONPATH para imports
ENV PATH="/app/services/atendente_core/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs/vizu_models/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_supabase_client/src:/app/libs/vizu_context_service/src:/app/libs/vizu_auth/src:/app/libs/vizu_tool_registry/src:/app/libs/vizu_prompt_management/src:/app/libs/vizu_elicitation_service/src:/app/libs/vizu_observability_bootstrap/src:/app/libs/vizu_agent_framework/src:/app/libs/vizu_llm_service/src:/app/libs/vizu_hitl_service/src:/app/libs/vizu_sql_factory/src:/app/libs/vizu_twilio_client/src"

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/services/atendente_core/.venv/bin/python -m uvicorn atendente_core.main:app --host 0.0.0.0 --port ${PORT:-8000}"]