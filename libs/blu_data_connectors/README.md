# blu_data_connectors

Shared data connectors for Blu data ingestion services.

## Overview

This library provides reusable data connectors for extracting data from various sources:
- **BigQuery**: Enterprise data warehouse connector
- **E-commerce platforms**: Shopify, VTEX, Loja Integrada

## Installation

```bash
# For e-commerce connectors only (lightweight)
poetry add blu-data-connectors --extras ecommerce

# For BigQuery connector (includes heavy dependencies)
poetry add blu-data-connectors --extras bigquery

# For all connectors
poetry add blu-data-connectors --extras all
```

## Usage

### E-commerce Connectors

```python
from blu_data_connectors.ecommerce import ShopifyConnector

credentials = {
    "shop_name": "myshop",
    "access_token": "..."
}

async with ShopifyConnector(credentials) as connector:
    products = await connector.get_products(limit=100)
```

### BigQuery Connector

```python
from blu_data_connectors.bigquery import BigQueryConnector
from google.cloud import bigquery

client = bigquery.Client()
connector = BigQueryConnector(client=client)

async for chunk_df in connector.extract_data("SELECT * FROM table"):
    # Process DataFrame chunk
    print(chunk_df.head())
```

## Available Connectors

| Connector | Module | Dependencies |
|-----------|--------|--------------|
| BigQuery | `blu_data_connectors.bigquery` | pandas, google-cloud-bigquery |
| Shopify | `blu_data_connectors.ecommerce` | httpx |
| VTEX | `blu_data_connectors.ecommerce` | httpx |
| Loja Integrada | `blu_data_connectors.ecommerce` | httpx |

## Design Principles

1. **Single Responsibility**: Each connector handles one data source
2. **Async-First**: All connectors use async/await
3. **Streaming**: Large datasets are yielded in chunks
4. **Optional Dependencies**: Only install what you need via extras

## Development

```bash
cd libs/blu_data_connectors
poetry install --all-extras
poetry run pytest
```
