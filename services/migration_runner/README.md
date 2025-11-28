# Vizu Migration Runner

This service is a container that is responsible for running database migrations.

## Overview

The Vizu Migration Runner is a simple container that is used to apply database migrations to the PostgreSQL database. It is configured in the `docker-compose.yml` file to run automatically when the `local` profile is used.

The container uses the `vizu-db` command-line interface from the `vizu_db_connector` library to apply the migrations.

### Key Technologies

*   **Migrations:** Alembic
*   **Database:** PostgreSQL
*   **Containerization:** Docker
