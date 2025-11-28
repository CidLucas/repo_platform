# Vizu Data Ingestion Worker

This service is a serverless worker responsible for the asynchronous processing of data ingestion jobs.

## Overview

The Vizu Data Ingestion Worker is designed to be deployed as a Google Cloud Function. It listens for messages on a Pub/Sub topic, which are triggered by the Data Ingestion API. When a message is received, the worker processes the ingestion job, which may involve fetching data from a source, transforming it, and writing it to the Vizu database.

### Key Technologies

*   **Cloud:** Google Cloud Platform (Cloud Functions, Pub/Sub)
*   **Data Manipulation:** Pandas
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Package Manager:** Poetry
