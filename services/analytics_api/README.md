# Vizu Analytics API

This service provides an API for data analytics in the Vizu application.

## Overview

The Vizu Analytics API is a FastAPI application that exposes endpoints for querying and analyzing data. It is responsible for transforming data from a "Silver" layer to a "Gold" layer, making it ready for consumption by the frontend or other services.

### Key Technologies

*   **Framework:** FastAPI
*   **Data Manipulation:** Pandas
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Package Manager:** Poetry
