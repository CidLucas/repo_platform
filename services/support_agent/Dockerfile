# Stage 1: Builder - Instala as dependências
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry==1.8.0

# Copia todas as libs necessárias (diretas + transitivas)
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

# Copia o serviço com seu código-fonte
COPY services/support_agent ./services/support_agent

# Instala dependências
WORKDIR /app/services/support_agent
RUN poetry lock && poetry install --no-root

# Stage 2: Final - Imagem mínima de produção
FROM python:3.11-slim

WORKDIR /app

# Copia .venv (contém todas as dependências)
COPY --from=builder /app/services/support_agent/.venv ./.venv

# Copia APENAS src/ das libs que são realmente dependências diretas
COPY --from=builder /app/libs/vizu_models/src ./libs/vizu_models/src
COPY --from=builder /app/libs/vizu_context_service/src ./libs/vizu_context_service/src
COPY --from=builder /app/libs/vizu_auth/src ./libs/vizu_auth/src
COPY --from=builder /app/libs/vizu_tool_registry/src ./libs/vizu_tool_registry/src
COPY --from=builder /app/libs/vizu_agent_framework/src ./libs/vizu_agent_framework/src
COPY --from=builder /app/libs/vizu_llm_service/src ./libs/vizu_llm_service/src

# Copia código fonte do serviço
COPY --from=builder /app/services/support_agent/src ./src

# PYTHONPATH para imports
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app/libs/vizu_models/src:/app/libs/vizu_context_service/src:/app/libs/vizu_auth/src:/app/libs/vizu_tool_registry/src:/app/libs/vizu_agent_framework/src:/app/libs/vizu_llm_service/src"

EXPOSE 8000

# Use Cloud Run PORT and run uvicorn from the copied venv to preserve shebangs.
CMD ["/bin/sh", "-c", "/app/.venv/bin/python -m uvicorn support_agent.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
