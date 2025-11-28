# Vizu Data Ingestion API

This microservice provides an API for ingesting data from various enterprise sources into the Vizu application.

## Overview

The Vizu Data Ingestion API is a FastAPI application that acts as a central point for data ingestion. It provides connectors for various data sources, such as Google BigQuery and Pub/Sub, and allows for the seamless integration of external data into the Vizu ecosystem.

### Key Technologies

*   **Framework:** FastAPI
*   **Cloud:** Google Cloud Platform (BigQuery, Pub/Sub)
*   **Data Manipulation:** Pandas
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Package Manager:** Poetry
