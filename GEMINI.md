# Project Vizu

## Project Overview

This project is a monorepo containing a complex, microservices-based application named "Vizu". The backend is built with Python and FastAPI, while the frontend is a React application. The system is designed to be an AI-powered platform to develop AI agents for several purposes, with features for data ingestion, processing, analytics, and a conversational interface.

### Key Technologies

*   **Backend:** Python, FastAPI, LangChain, Ollama
*   **Frontend:** React, Vite, Chakra UI, Leaflet, Recharts
*   **Databases:** PostgreSQL, Redis, Qdrant
*   **Infrastructure:** Docker, Docker Compose, OpenTelemetry

### Architecture

The project follows a microservices architecture, with various services communicating with each other. The `docker-compose.yml` file defines the services and their relationships. Key services include:

*   `atendente_core`: The core conversational AI service.
*   `clients_api`: Manages client data.
*   `file_upload_api` & `file_processing_worker`: Handle file uploads and asynchronous processing.
*   `analytics_api`: Provides data analytics endpoints.
*   `vizu_dashboard`: The frontend React application.

## Building and Running

The project is containerized using Docker and orchestrated with Docker Compose.

### Local Development

To run the application in a local development environment, use the following command:

```bash
docker-compose --profile local up
```

This will start all the necessary services, including the local database and other infrastructure components.

### Production

To run the application in a production-like environment, use the following command:

```bash
docker-compose up
```

This will start the core application services.

## Development Conventions

### Python

*   The Python services use [Poetry](https://python-poetry.org/) for dependency management.
*   The backend code is formatted with `ruff`.
*   Tests are written with `pytest`.

### Frontend

*   The frontend is a React application built with [Vite](https://vitejs.dev/).
*   The code is linted with `eslint`.

### Database Migrations

Database migrations are managed with Alembic. The `migrator` service in `docker-compose.yml` runs the migrations automatically when the `local` profile is used. To run migrations manually, you can use the `vizu-db` CLI.

*TODO: Add instructions on how to use the `vizu-db` CLI for manual migrations.*
