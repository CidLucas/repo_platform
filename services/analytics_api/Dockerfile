# Estágio 1: Builder - Reúne *todos* os fontes e constrói o venv
FROM python:3.11-slim as builder

# Instala o Poetry
RUN pip install --no-cache-dir poetry==1.8.0
ENV POETRY_NO_INTERACTION=1

# --- MUDANÇA CRÍTICA: Criar venv DENTRO da pasta do projeto ---
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app

# 1. COPIA as libs (pastas inteiras, incluindo README.md)
COPY ./libs ./libs

# 2. COPIA a API (pasta inteira)
COPY ./services/analytics_api ./services/analytics_api

# 3. MUDE o WORKDIR para o diretório do serviço
WORKDIR /app/services/analytics_api

# 4. INSTALE. O Poetry irá encontrar o README.md em ../../libs/
RUN poetry install --no-root

# -----------------------------------------------------

# Estágio 2: Final - Apenas o Runtime
FROM python:3.11-slim

# --- MUDANÇA CRÍTICA: WORKDIR é a pasta do serviço ---
WORKDIR /app/services/analytics_api

# 5. COPIA o venv (do builder para o MESMO caminho exato)
# Isto resolve o erro "shebang" e "path relativo"
COPY --from=builder /app/services/analytics_api/.venv ./.venv

# 6. COPIA o código-fonte
# Copia o 'src' da API para dentro do WORKDIR atual
COPY --from=builder /app/services/analytics_api/src ./src
# Copia as libs para um local absoluto FORA do WORKDIR
COPY --from=builder /app/libs /app/libs

# 7. AJUSTE o PATH (Absoluto, apontando para o venv no WORKDIR)
ENV PATH="/app/services/analytics_api/.venv/bin:$PATH"

# 8. AJUSTE o PYTHONPATH (Relativo ao WORKDIR)
ENV PYTHONPATH="src:../../libs/vizu_db_connector/src:../../libs/vizu_models/src"

# 9. DEFINA o comando de execução
EXPOSE 80
CMD ["uvicorn", "analytics_api.main:app", "--host", "0.0.0.0", "--port", "80"]