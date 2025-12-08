# Estágio 1: Builder - Instala as dependências
FROM python:3.11-slim AS builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app

RUN pip install poetry

# Copia libs necessárias (diretas + transitivas)
COPY libs/vizu_models ./libs/vizu_models
COPY libs/vizu_db_connector ./libs/vizu_db_connector
COPY libs/vizu_supabase_client ./libs/vizu_supabase_client
COPY libs/vizu_context_service ./libs/vizu_context_service
COPY libs/vizu_auth ./libs/vizu_auth
COPY libs/vizu_tool_registry ./libs/vizu_tool_registry
COPY libs/vizu_elicitation_service ./libs/vizu_elicitation_service
COPY libs/vizu_observability_bootstrap ./libs/vizu_observability_bootstrap
COPY libs/vizu_agent_framework ./libs/vizu_agent_framework
COPY libs/vizu_llm_service ./libs/vizu_llm_service

# Copia pyproject e instala dependências
COPY services/support_agent/pyproject.toml services/support_agent/poetry.lock* ./services/support_agent/
WORKDIR /app/services/support_agent
RUN poetry lock && poetry install --no-root

# ----------------------------------------------------------------
# Estágio 2: Final - Imagem mínima de produção
FROM python:3.11-slim

WORKDIR /app

# Copia .venv
COPY --from=builder /app/services/support_agent/.venv ./.venv

# Copia apenas os src/ das libs (não o pyproject.toml)
COPY libs/vizu_models/src ./libs/vizu_models/src
COPY libs/vizu_db_connector/src ./libs/vizu_db_connector/src
COPY libs/vizu_supabase_client/src ./libs/vizu_supabase_client/src
COPY libs/vizu_context_service/src ./libs/vizu_context_service/src
COPY libs/vizu_auth/src ./libs/vizu_auth/src
COPY libs/vizu_tool_registry/src ./libs/vizu_tool_registry/src
COPY libs/vizu_elicitation_service/src ./libs/vizu_elicitation_service/src
COPY libs/vizu_observability_bootstrap/src ./libs/vizu_observability_bootstrap/src
COPY libs/vizu_agent_framework/src ./libs/vizu_agent_framework/src
COPY libs/vizu_llm_service/src ./libs/vizu_llm_service/src

# Copia código fonte do serviço
COPY services/support_agent/src ./src

# PYTHONPATH para imports
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs/vizu_models/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_supabase_client/src:/app/libs/vizu_context_service/src:/app/libs/vizu_auth/src:/app/libs/vizu_tool_registry/src:/app/libs/vizu_elicitation_service/src:/app/libs/vizu_observability_bootstrap/src:/app/libs/vizu_agent_framework/src:/app/libs/vizu_llm_service/src"

EXPOSE 8000

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "support_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
