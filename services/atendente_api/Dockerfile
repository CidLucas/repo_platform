# 1. Estágio de Build ('builder') - Nenhuma mudança aqui
FROM --platform=linux/amd64 python:3.11-slim as builder
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app
RUN pip install poetry
COPY libs ./libs
COPY services/atendente_api/pyproject.toml services/atendente_api/poetry.lock ./services/atendente_api/
WORKDIR /app/services/atendente_api
RUN poetry install --no-root --without dev

# 2. Estágio de Produção (Imagem Final)
FROM python:3.11-slim
WORKDIR /app

# Copia o ambiente virtual
COPY --from=builder /app/services/atendente_api/.venv ./.venv

# --- MUDANÇA 1: Copiar as bibliotecas compartilhadas ---
# Copia a pasta 'libs' do estágio de build para a imagem final.
COPY --from=builder /app/libs ./libs

# Copia o código-fonte da aplicação
COPY services/atendente_api/src ./src

# --- MUDANÇA 2: Atualizar o PYTHONPATH ---
# Adiciona /app/libs ao caminho de busca do Python.
# O ':' é o separador de caminhos no Linux.
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/libs"

EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "atendente_api.main:app", "--host", "0.0.0.0", "--port", "8000"]