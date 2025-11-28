# Vizu Ollama Service

This service runs the Ollama service in a container.

## Overview

The Vizu Ollama Service is a container that provides a running instance of the Ollama service. It is used by the `atendente_core` and other services to interact with large language models.

The service is built on top of the official `ollama/ollama` Docker image and includes a custom entrypoint script to configure the service on startup.

### Key Technologies

*   **LLM:** Ollama
*   **Containerization:** Docker
