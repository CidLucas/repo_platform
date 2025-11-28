# Vizu Clients API

This service provides an API for managing Vizu clients and their external service credentials.

## Overview

The Vizu Clients API is a FastAPI application that handles the creation, retrieval, and management of Vizu clients. It also stores and encrypts credentials for external services that are used by the Vizu application.

### Key Technologies

*   **Framework:** FastAPI
*   **Encryption:** Cryptography
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Observability:** OpenTelemetry (via `vizu_observability_bootstrap`)
*   **Package Manager:** Poetry
