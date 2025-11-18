# Padrão Vizu: Baseado no Dockerfile do file_processing_worker

# --- ESTÁGIO 1: BUILDER ---
FROM python:3.11-slim as builder


ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app
RUN pip install poetry
COPY . .

# Aponta para o diretório do nosso novo serviço de embedding
WORKDIR /app/services/embedding_service
# Instala as dependências definidas no pyproject.toml (Passo 3)
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    poetry install --no-root
# --- ESTÁGIO 2: FINAL (PRODUÇÃO) ---
FROM python:3.11-slim as final

RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs"
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Copia o .venv do embedding_service
COPY --from=builder --chown=appuser:appuser /app/services/embedding_service/.venv ./.venv
# Copia as libs (igual ao molde)
COPY --from=builder --chown=appuser:appuser /app/libs ./libs

# Copia o código-fonte do embedding_service, respeitando a sua estrutura
# Origem: ./services/embedding_service/src/embedding_service
# Destino: ./embedding_service
COPY --chown=appuser:appuser ./services/embedding_service/src/embedding_service ./embedding_service

USER appuser
# Expõe a porta que definimos para este serviço
EXPOSE 11435

# Aponta o CMD para o módulo 'embedding_service' (que copiamos acima)
# e seu arquivo 'main', variável 'app', na porta 11435.
CMD ["/home/appuser/app/.venv/bin/python", "-m", "uvicorn", "embedding_service.main:app", "--host", "0.0.0.0", "--port", "11435"]