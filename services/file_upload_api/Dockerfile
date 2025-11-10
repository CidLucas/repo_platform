# Padrão Vizu: Baseado no Dockerfile da clientes_finais_api

# --- ESTÁGIO 1: BUILDER ---
FROM python:3.11-slim as builder

# Define o WORKDIR raiz do monorepo
WORKDIR /app

# Instala o Poetry
RUN pip install poetry

# Copia TUDO (contexto do monorepo)
# Isso é necessário para o Poetry resolver as dependências 'path' das libs
COPY . .

# Define o WORKDIR específico do serviço para instalar as dependências
WORKDIR /app/services/file_upload_api

# Instala apenas as dependências de PRODUÇÃO.
RUN poetry install --no-dev --no-root

# --- ESTÁGIO 2: FINAL (PRODUÇÃO) ---
FROM python:3.11-slim as final

# Padrão Vizu: Não rodar como root
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Padrão Vizu: Ajuste do PYTHONPATH
ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs"
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Copia o ambiente virtual com as dependências instaladas do 'builder'
COPY --from=builder --chown=appuser:appuser /app/services/file_upload_api/.venv ./.venv

# Padrão Vizu: Copia TODAS as libs compartilhadas do 'builder'
COPY --from=builder --chown=appuser:appuser /app/libs ./libs

# Padrão Vizu: Copia o código-fonte do serviço
COPY --chown=appuser:appuser ./services/file_upload_api/src/file_upload_api ./file_upload_api

USER appuser

EXPOSE 8000

# Padrão Vizu: Comando de execução
CMD ["/home/appuser/app/.venv/bin/python", "-m", "uvicorn", "file_upload_api.main:app", "--host", "0.0.0.0", "--port", "8000"]