# Em: services/clientes_finais_api/Dockerfile

# ---- 1. Builder Stage ----
# (Esta parte permanece exatamente a mesma)
FROM python:3.11-slim as builder
RUN pip install poetry
# ... (igual ao que já fizemos) ...
WORKDIR /app
COPY ./libs ./libs
COPY ./services/clientes_finais_api/pyproject.toml ./services/clientes_finais_api/poetry.lock* ./services/clientes_finais_api/
WORKDIR /app/services/clientes_finais_api
RUN poetry install --no-root


# ---- 2. Final Stage ----
# (Aqui faremos as adições)
FROM python:3.11-slim

RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs"

COPY --from=builder /app/services/clientes_finais_api/.venv ./.venv
COPY --from=builder /app/libs ./libs
COPY --chown=appuser:appuser ./services/clientes_finais_api/src/clientes_finais_api ./clientes_finais_api

# --- CORREÇÃO DEFINITIVA DA MIGRAÇÃO ---
# 1. Copia os arquivos de configuração do Alembic da biblioteca compartilhada
#    para a raiz do diretório de trabalho da nossa API.




# 3. Define o entrypoint. Este script será executado ANTES do CMD.


EXPOSE 8000

# 4. Define o comando padrão, que será passado como argumento ("$@") para o entrypoint.
CMD ["/home/appuser/app/.venv/bin/python", "-m", "uvicorn", "clientes_finais_api.main:app", "--host", "0.0.0.0", "--port", "8000"]