# Vizu Data Ingestion API

> [!WARNING]
> **DEPRECATED** - This service is deprecated as of February 2026.
> Data ingestion has been migrated to Supabase FDW (Foreign Data Wrapper) + RPCs.
> The dashboard now calls `sincronizar_dados_cliente` RPC directly via Supabase client.
> BigQuery connections use `create_bigquery_server` and `create_bigquery_foreign_table` RPCs.
> See `apps/vizu_dashboard/src/services/connectorService.ts` for the new implementation.
> This service remains for reference only and will be removed in a future release.

This microservice provides an API for ingesting data from various enterprise sources into the Vizu application.

## Overview

The Vizu Data Ingestion API is a FastAPI application that acts as a central point for data ingestion. It provides connectors for various data sources, such as Google BigQuery and Pub/Sub, and allows for the seamless integration of external data into the Vizu ecosystem.

### Key Technologies

*   **Framework:** FastAPI
*   **Cloud:** Google Cloud Platform (BigQuery, Pub/Sub)
*   **Data Manipulation:** Pandas
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Package Manager:** Poetry
