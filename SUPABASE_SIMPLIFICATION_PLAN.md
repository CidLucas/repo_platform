# Supabase BigQuery Wrapper - Architecture Simplification Plan

## Current Architecture (Complex & Heavy)

```
┌─────────────────────────────────────────────────────────────┐
│                    data_ingestion_api                        │
│  - Receives credentials                                      │
│  - Validates connection via BigQuery SDK (~150MB)           │
│  - Publishes job to Pub/Sub (~50MB)                         │
│  - Dependencies: google-cloud-bigquery, google-cloud-pubsub │
│  Total Size: ~200MB                                          │
└──────────────────┬──────────────────────────────────────────┘
                   │ pub/sub message
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              data_ingestion_worker (Cloud Function)          │
│  - Triggered by Pub/Sub message                             │
│  - Uses BigQueryConnector to extract data                   │
│  - Uses pandas to transform                                 │
│  - Writes to Supabase                                       │
│  Dependencies: vizu-data-connectors[bigquery], pandas       │
│  Total Size: ~450MB                                          │
└──────────────────────────────────────────────────────────────┘
```

**Problems:**
- 🔴 Heavy Google Cloud dependencies (~150MB for BigQuery SDK)
- 🔴 Complex Pub/Sub messaging infrastructure
- 🔴 Two separate services with different responsibilities
- 🔴 BigQuery SDK needed just to execute SQL queries
- 🔴 Circular complexity in data flow

## New Architecture (Simple & Lightweight)

```
┌─────────────────────────────────────────────────────────────┐
│                      Supabase Database                       │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  BigQuery Foreign Data Wrapper (FDW)   │                │
│  │  - Foreign Server: bigquery_server     │                │
│  │  - Foreign Tables map to BigQuery      │                │
│  │  - Direct SQL queries to BigQuery      │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  Native Supabase Tables                │                │
│  │  - vizu_credentials                     │                │
│  │  - vizu_ingestion_jobs                  │                │
│  │  - vizu_ingestion_data                  │                │
│  └────────────────────────────────────────┘                │
└──────────────────┬──────────────────────────────────────────┘
                   │ Direct SQL queries
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    data_ingestion_api                        │
│  - Receives credentials                                      │
│  - Stores in Supabase (vizu_credentials)                    │
│  - Creates BigQuery foreign tables via SQL                  │
│  - Executes data extraction via SQL                         │
│  - NO BigQuery SDK needed!                                  │
│  - NO Pub/Sub needed!                                       │
│  Dependencies: vizu-supabase-client, vizu-data-connectors   │
│  Total Size: ~80MB (vs 200MB before)                        │
└──────────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ **120MB smaller** - No BigQuery SDK, no Pub/Sub
- ✅ **Single service** - No worker needed for BigQuery
- ✅ **Direct SQL** - Query BigQuery via Supabase foreign tables
- ✅ **Simpler flow** - API → Supabase FDW → BigQuery → Supabase tables
- ✅ **Unified authentication** - Service account stored once in Supabase Vault
- ✅ **No message queue** - Synchronous or async via Supabase Edge Functions

## Implementation Plan

### Phase 1: Setup Supabase BigQuery Wrapper

**File: `supabase/migrations/YYYYMMDD_setup_bigquery_wrapper.sql`**

```sql
-- 1. Enable wrappers extension
create extension if not exists wrappers with schema extensions;

-- 2. Enable BigQuery FDW
create foreign data wrapper bigquery_wrapper
  handler big_query_fdw_handler
  validator big_query_fdw_validator;

-- 3. Create schema for BigQuery foreign tables
create schema if not exists bigquery;

-- 4. Function to create BigQuery foreign server per client
create or replace function create_bigquery_server(
  client_id text,
  service_account_key jsonb,
  project_id text,
  dataset_id text
) returns text as $$
declare
  server_name text;
  key_id text;
begin
  server_name := 'bigquery_' || client_id;

  -- Store service account in Vault
  select vault.create_secret(
    service_account_key::text,
    server_name || '_key',
    'BigQuery service account for ' || client_id
  ) into key_id;

  -- Create foreign server
  execute format(
    'create server if not exists %I
     foreign data wrapper bigquery_wrapper
     options (
       sa_key_id %L,
       project_id %L,
       dataset_id %L
     )',
    server_name,
    key_id,
    project_id,
    dataset_id
  );

  return server_name;
end;
$$ language plpgsql security definer;

-- 5. Function to create foreign table dynamically
create or replace function create_bigquery_foreign_table(
  client_id text,
  table_name text,
  bigquery_table text,
  columns jsonb,
  location text default 'US'
) returns text as $$
declare
  server_name text;
  foreign_table_name text;
  column_defs text;
begin
  server_name := 'bigquery_' || client_id;
  foreign_table_name := 'bigquery.' || client_id || '_' || table_name;

  -- Build column definitions from jsonb
  -- Format: [{"name": "id", "type": "bigint"}, {"name": "name", "type": "text"}]
  select string_agg(col->>'name' || ' ' || col->>'type', ', ')
  from jsonb_array_elements(columns) as col
  into column_defs;

  -- Create foreign table
  execute format(
    'create foreign table if not exists %s (%s)
     server %I
     options (
       table %L,
       location %L
     )',
    foreign_table_name,
    column_defs,
    server_name,
    bigquery_table,
    location
  );

  return foreign_table_name;
end;
$$ language plpgsql security definer;

-- 6. Function to extract data from BigQuery to Supabase
create or replace function extract_bigquery_data(
  client_id text,
  source_table text,
  destination_table text,
  column_mapping jsonb default null
) returns bigint as $$
declare
  rows_inserted bigint;
  select_clause text;
  insert_query text;
begin
  -- Build select clause with optional column mapping
  if column_mapping is null then
    select_clause := '*';
  else
    -- Format: {"source_col": "dest_col", ...}
    select string_agg(
      key || ' as ' || value,
      ', '
    )
    from jsonb_each_text(column_mapping)
    into select_clause;
  end if;

  -- Execute insert from foreign table to native table
  execute format(
    'insert into %I select %s from %I',
    destination_table,
    select_clause,
    source_table
  );

  get diagnostics rows_inserted = row_count;
  return rows_inserted;
end;
$$ language plpgsql security definer;
```

### Phase 2: Update Data Ingestion API

**Remove:**
- ❌ BigQueryConnector class (use SQL instead)
- ❌ Pub/Sub publisher service
- ❌ google-cloud-bigquery dependency
- ❌ google-cloud-pubsub dependency
- ❌ BigQuery-specific schemas

**Add:**
- ✅ Supabase RPC functions for BigQuery operations
- ✅ New service: `BigQueryWrapperService`
- ✅ Simplified credential flow

**New File: `services/data_ingestion_api/src/data_ingestion_api/services/bigquery_wrapper_service.py`**

```python
"""
Service for managing BigQuery data extraction via Supabase Foreign Data Wrapper.
Replaces the heavy BigQueryConnector with lightweight SQL-based approach.
"""

import logging
from typing import Any

from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class BigQueryWrapperService:
    """
    Manages BigQuery integration using Supabase's BigQuery FDW.

    This eliminates the need for:
    - google-cloud-bigquery SDK (~150MB)
    - Pub/Sub messaging infrastructure
    - Separate worker service for BigQuery
    """

    def __init__(self):
        self.supabase = get_supabase_client()

    async def setup_client_bigquery(
        self,
        client_id: str,
        service_account_key: dict[str, Any],
        project_id: str,
        dataset_id: str
    ) -> str:
        """
        Sets up BigQuery foreign server for a client.

        Args:
            client_id: Unique client identifier
            service_account_key: Google Cloud service account JSON
            project_id: GCP project ID
            dataset_id: BigQuery dataset ID

        Returns:
            Foreign server name created
        """
        result = await self.supabase.rpc(
            'create_bigquery_server',
            {
                'client_id': client_id,
                'service_account_key': service_account_key,
                'project_id': project_id,
                'dataset_id': dataset_id
            }
        )

        logger.info(f"Created BigQuery server for client {client_id}: {result.data}")
        return result.data

    async def create_foreign_table(
        self,
        client_id: str,
        table_name: str,
        bigquery_table: str,
        columns: list[dict[str, str]],
        location: str = 'US'
    ) -> str:
        """
        Creates a foreign table mapping to BigQuery.

        Args:
            client_id: Client identifier
            table_name: Local table name
            bigquery_table: BigQuery source table name
            columns: List of {"name": "col", "type": "bigint"}
            location: BigQuery data location

        Returns:
            Foreign table name created
        """
        result = await self.supabase.rpc(
            'create_bigquery_foreign_table',
            {
                'client_id': client_id,
                'table_name': table_name,
                'bigquery_table': bigquery_table,
                'columns': columns,
                'location': location
            }
        )

        logger.info(f"Created foreign table: {result.data}")
        return result.data

    async def extract_data(
        self,
        client_id: str,
        source_table: str,
        destination_table: str,
        column_mapping: dict[str, str] | None = None
    ) -> int:
        """
        Extracts data from BigQuery foreign table to Supabase native table.

        Args:
            client_id: Client identifier
            source_table: Foreign table name
            destination_table: Destination native table
            column_mapping: Optional {"source": "dest"} mapping

        Returns:
            Number of rows inserted
        """
        result = await self.supabase.rpc(
            'extract_bigquery_data',
            {
                'client_id': client_id,
                'source_table': source_table,
                'destination_table': destination_table,
                'column_mapping': column_mapping
            }
        )

        logger.info(f"Extracted {result.data} rows from BigQuery to {destination_table}")
        return result.data

    async def query_bigquery_direct(
        self,
        foreign_table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        Queries BigQuery foreign table directly via SQL.

        Args:
            foreign_table: Foreign table name (e.g., 'bigquery.client_products')
            filters: Optional WHERE clause filters
            limit: Max rows to return

        Returns:
            Query results as list of dicts
        """
        query = self.supabase.table(foreign_table).select('*')

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        result = await query.limit(limit).execute()
        return result.data

    async def validate_connection(
        self,
        client_id: str
    ) -> bool:
        """
        Validates BigQuery connection by querying the foreign server.

        Args:
            client_id: Client identifier

        Returns:
            True if connection is valid
        """
        try:
            # Try a simple query to validate connection
            server_name = f'bigquery_{client_id}'

            # Query information_schema to check if server exists
            result = await self.supabase.rpc(
                'validate_foreign_server',
                {'server_name': server_name}
            )

            return result.data
        except Exception as e:
            logger.error(f"BigQuery connection validation failed: {e}")
            return False
```

### Phase 3: Remove BigQueryConnector from vizu_data_connectors

Since we're using Supabase FDW, we no longer need the BigQueryConnector class:

**Update: `libs/vizu_data_connectors/pyproject.toml`**

```toml
[tool.poetry.extras]
# Remove BigQuery extra - no longer needed!
ecommerce = []
all = []  # Just ecommerce now
```

**Remove:**
- `libs/vizu_data_connectors/src/vizu_data_connectors/bigquery/` (entire directory)

### Phase 4: Simplify Worker (or eliminate it for BigQuery)

**Option A: Keep worker only for e-commerce**
- Worker only handles Shopify, VTEX, Loja Integrada
- BigQuery goes through API → Supabase FDW directly

**Option B: Eliminate worker entirely**
- Use Supabase Edge Functions for async processing
- All extraction happens via SQL in Supabase

### Phase 5: Update Dependencies

**API pyproject.toml:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.111.0"
uvicorn = {extras = ["standard"], version = "^0.30.1"}
pydantic = "^2.7.4"
psycopg2-binary = "^2.9.9"

# REMOVED: google-cloud-bigquery, google-cloud-pubsub, pandas, numpy, pyarrow

# VIZU INTERNAL LIBS
vizu-db-connector = {path = "../../libs/vizu_db_connector", develop = true}
vizu-auth = {path = "../../libs/vizu_auth", develop = true}
vizu-models = {path = "../../libs/vizu_models", develop = true}
vizu-supabase-client = {path = "../../libs/vizu_supabase_client", develop = true}
vizu-data-connectors = {path = "../../libs/vizu_data_connectors", develop = true, extras = ["ecommerce"]}
```

## Migration Steps

1. ✅ **Create Supabase migration** for BigQuery wrapper setup
2. ✅ **Implement BigQueryWrapperService** in API
3. ✅ **Update credential endpoints** to use new service
4. ✅ **Remove BigQueryConnector** from vizu_data_connectors
5. ✅ **Remove Pub/Sub** dependencies and code
6. ✅ **Update tests** to use mocked Supabase RPC calls
7. ✅ **Deploy and test** with real BigQuery data

## Expected Results

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| **API Dependencies** | google-cloud-bigquery (150MB) + pubsub (50MB) | None | **-200MB** |
| **API Docker Image** | ~200MB | ~80MB | **-120MB (60%)** |
| **Worker Needed?** | Yes (for BigQuery) | No (use Supabase FDW) | **-1 service** |
| **Code Complexity** | High (2 services, Pub/Sub, SDK) | Low (SQL queries) | **-500 LOC** |
| **Response Time** | Async (Pub/Sub delay) | Sync/Async (configurable) | **Faster** |

## Next Steps

Ready to implement? I'll:
1. Create the Supabase migration SQL
2. Implement BigQueryWrapperService
3. Update the API routes
4. Remove BigQuery SDK dependencies
5. Update tests

Should I proceed?
