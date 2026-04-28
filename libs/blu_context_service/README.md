# Blu Context Service

This library provides a client context service for the Blu application.

## Overview

The Blu Context Service is a library that provides an agnostic way to access client context from the database and cache from Redis. It is used by various services in the Blu monorepo to get information about the current client.

### Key Technologies

*   **Database:** PostgreSQL (via `blu_db_connector`)
*   **Cache:** Redis
*   **Package Manager:** Poetry
