# Vizu Data Processing Worker

This service is an asynchronous worker responsible for the Extraction, Transformation, and Load (ETL/ELT) of Vizu client data.

## Overview

The Vizu Data Processing Worker is an asynchronous worker that performs ETL/ELT tasks on client data. It is triggered by events in the Vizu ecosystem, such as new data being ingested. The worker fetches the data, transforms it into the required format, and loads it into the appropriate destination, which could be the Vizu database or another data store.

### Key Technologies

*   **Cloud:** Google Cloud Platform (Pub/Sub, Cloud Storage)
*   **Data Manipulation:** Pandas
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Package Manager:** Poetry
