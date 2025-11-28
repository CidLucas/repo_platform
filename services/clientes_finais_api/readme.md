# Vizu Clientes Finais API

This service provides an API for managing "Clientes Finais" (End Customers) in the Vizu application.

## Overview

The Vizu Clientes Finais API is a FastAPI application that provides CRUD (Create, Read, Update, Delete) operations for end customers. It is used by other services to manage customer data.

### Key Technologies

*   **Framework:** FastAPI
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Observability:** OpenTelemetry (via `vizu_observability_bootstrap`)
*   **Package Manager:** Poetry
