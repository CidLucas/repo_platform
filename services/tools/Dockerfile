FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install poetry

COPY pyproject.toml poetry.lock* /app/
COPY src /app/src

WORKDIR /app
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-root

ENV PYTHONPATH="/app/src"
EXPOSE 8000
CMD ["uvicorn", "tools.main:app", "--host", "0.0.0.0", "--port", "8000"]
