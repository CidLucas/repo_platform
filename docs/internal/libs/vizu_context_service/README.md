# Vizu Context Service

This library provides a client context service for the Vizu application.

## Overview

The Vizu Context Service is a library that provides an agnostic way to access client context from the database and cache from Redis. It is used by various services in the Vizu monorepo to get information about the current client.

### Key Technologies

*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Cache:** Redis
*   **Package Manager:** Poetry
