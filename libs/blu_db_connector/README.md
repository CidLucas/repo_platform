# Blu DB Connector

This library provides database connectivity and migration management for the Blu project.

## Overview

The Blu DB Connector is a central library for all database-related operations in the Blu application. It uses SQLAlchemy for object-relational mapping, Alembic for database migrations, and `psycopg2-binary` as the PostgreSQL driver.

### Key Technologies

*   **ORM:** SQLAlchemy
*   **Migrations:** Alembic
*   **Driver:** psycopg2-binary
*   **Package Manager:** Poetry

## Database Migrations

This library includes a command-line interface (CLI) for managing database migrations.

### Running Migrations

To run database migrations, you can use the `blu-db` command:

```bash
poetry run blu-db migrate
```

This command is also used in the `migrator` service in the `docker-compose.yml` file to automatically run migrations on startup.
