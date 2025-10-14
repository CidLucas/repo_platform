# ---- 1. Builder Stage ----
# Objetivo: Instalar dependências de forma eficiente usando o cache do Docker.
FROM python:3.11-slim as builder

# Instala o Poetry
RUN pip install poetry

# Define variáveis de ambiente para o Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# --- CORREÇÃO ESTRUTURAL ---
# Copia a pasta de bibliotecas para o local exato que o pyproject.toml espera.
WORKDIR /app
COPY ./libs ./libs

# Agora, cria a estrutura de pastas do serviço e copia os arquivos do projeto para dentro dela.
WORKDIR /app/services/clientes_finais_api
COPY ./services/clientes_finais_api/pyproject.toml ./services/clientes_finais_api/poetry.lock ./

# Com a estrutura de pastas recriada, os caminhos relativos agora funcionam.
# --no-dev para não instalar dependências de desenvolvimento como o pytest.
RUN poetry install --no-root


# ---- 2. Final Stage ----
# Objetivo: Construir a imagem de produção final, leve e segura.
FROM python:3.11-slim

# Cria um usuário não-root para rodar a aplicação.
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Define o PYTHONPATH para que o Python encontre o código da aplicação e as libs.
ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs"

# Copia os artefatos do estágio builder
# --- CORREÇÃO DO CAMINHO DO .VENV ---
COPY --from=builder /app/services/clientes_finais_api/.venv ./.venv
COPY --from=builder /app/libs ./libs

# Copia o código fonte da aplicação a partir da RAIZ do contexto.
COPY --chown=appuser:appuser ./services/clientes_finais_api/src/clientes_finais_api ./clientes_finais_api

EXPOSE 8000

# Comando para iniciar a aplicação, usando o python do ambiente virtual.
CMD ["/home/appuser/app/.venv/bin/python", "-m", "uvicorn", "clientes_finais_api.main:app", "--host", "0.0.0.0", "--port", "8000"]