# Padrão Vizu: Optimized Dockerfile for embedding_service
# Uses CPU-only PyTorch to reduce image size from 11.8GB to ~1.5GB

# --- ESTÁGIO 1: BUILDER ---
FROM python:3.11-slim AS builder

# Install poetry
RUN pip install poetry

# Setup virtual environment
ENV VIRTUAL_ENV=/opt/pysetup/.venv
ENV PATH="/opt/pysetup/.venv/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app/services/embedding_service

# Copy lib dependencies first (for caching)
COPY ./libs/vizu_parsers /app/libs/vizu_parsers

# Copy only pyproject.toml and poetry.lock for dependency installation
COPY ./services/embedding_service/pyproject.toml ./services/embedding_service/poetry.lock* ./

# Create venv and install:
# 1. CPU-only PyTorch first (avoids 6.6GB of GPU deps)
# 2. sentence-transformers from PyPI (uses already installed torch)
# 3. Other dependencies via poetry
RUN python -m venv $VIRTUAL_ENV && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir sentence-transformers && \
    poetry install --no-root --no-interaction


# --- ESTÁGIO 2: FINAL (PRODUÇÃO) ---
FROM python:3.11-slim AS final

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user and the cache directory with proper ownership
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/.cache/huggingface && \
    chown -R appuser:appuser /home/appuser/.cache

USER appuser
WORKDIR /home/appuser/app

# PYTHONPATH includes libs for vizu_parsers import
ENV PYTHONPATH="/home/appuser/app:/home/appuser/app/libs/vizu_parsers/src"

# Copy virtual environment from builder
COPY --from=builder /opt/pysetup/.venv /opt/pysetup/.venv
ENV PATH="/opt/pysetup/.venv/bin:$PATH"

# Copy vizu_parsers lib
COPY --chown=appuser:appuser ./libs/vizu_parsers/src/vizu_parsers ./libs/vizu_parsers/src/vizu_parsers

# Copy only the service source code
COPY --chown=appuser:appuser ./services/embedding_service/src/embedding_service ./embedding_service

# Expose port
EXPOSE 11435

# Run the service
CMD ["/opt/pysetup/.venv/bin/python", "-m", "uvicorn", "embedding_service.main:app", "--host", "0.0.0.0", "--port", "11435"]