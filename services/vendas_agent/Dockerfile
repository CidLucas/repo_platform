# Stage 1: Builder - Instala as dependências
FROM python:3.11-slim as builder

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_HTTP_TIMEOUT=300
ENV POETRY_REQUESTS_TIMEOUT=300

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
COPY services/vendas_agent ./services/vendas_agent

# Instala dependências
WORKDIR /app/services/vendas_agent
RUN poetry install --no-root

# Stage 2: Final - Imagem mínima de produção
FROM python:3.11-slim

# WORKDIR must match builder path so shebangs in .venv work correctly
WORKDIR /app/services/vendas_agent

# Copy .venv to SAME path as builder (shebangs reference this absolute path)
COPY --from=builder /app/services/vendas_agent/.venv ./.venv

# Copy lib src directories to /app/libs (matching PYTHONPATH)
COPY --from=builder /app/libs/vizu_models/src /app/libs/vizu_models/src
COPY --from=builder /app/libs/vizu_db_connector/src /app/libs/vizu_db_connector/src
COPY --from=builder /app/libs/vizu_supabase_client/src /app/libs/vizu_supabase_client/src
COPY --from=builder /app/libs/vizu_context_service/src /app/libs/vizu_context_service/src
COPY --from=builder /app/libs/vizu_auth/src /app/libs/vizu_auth/src
COPY --from=builder /app/libs/vizu_tool_registry/src /app/libs/vizu_tool_registry/src
COPY --from=builder /app/libs/vizu_elicitation_service/src /app/libs/vizu_elicitation_service/src
COPY --from=builder /app/libs/vizu_observability_bootstrap/src /app/libs/vizu_observability_bootstrap/src
COPY --from=builder /app/libs/vizu_agent_framework/src /app/libs/vizu_agent_framework/src
COPY --from=builder /app/libs/vizu_llm_service/src /app/libs/vizu_llm_service/src

# Copy service source code
COPY --from=builder /app/services/vendas_agent/src ./src

# PATH and PYTHONPATH - use absolute paths for reliability (include ALL libs)
ENV PATH="/app/services/vendas_agent/.venv/bin:$PATH" \
    PYTHONPATH="/app/services/vendas_agent/src:/app/libs/vizu_models/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_supabase_client/src:/app/libs/vizu_context_service/src:/app/libs/vizu_auth/src:/app/libs/vizu_tool_registry/src:/app/libs/vizu_elicitation_service/src:/app/libs/vizu_observability_bootstrap/src:/app/libs/vizu_agent_framework/src:/app/libs/vizu_llm_service/src"

EXPOSE 8000

# Use Cloud Run PORT and run uvicorn from the copied venv.
CMD ["/bin/sh", "-c", "/app/services/vendas_agent/.venv/bin/uvicorn vendas_agent.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
