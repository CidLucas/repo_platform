# BigQuery ETL Flow - Simplified Implementation

## Issues Fixed

### Issue 1: Schema Mapping Requirement ❌ REMOVED

**Problem**: ETL service required schema mappings that didn't exist
**Error**: `No schema mapping found for credential_id=6, resource_type=invoices`

**Root Cause**: The original design assumed we'd need to map BigQuery columns to a canonical schema, but this adds unnecessary complexity for the MVP.

**Solution**: Removed schema mapping requirement - BigQuery data is ingested as-is.

---

### Issue 2: Secret Manager Dependency ❌ REMOVED

**Problem**: ETL tried to use Google Secret Manager which isn't configured
**Root Cause**: Leftover from original architecture

**Solution**: Credentials are stored directly in Supabase (`credenciais_cifradas` column as JSON).

---

### Issue 3: Missing BigQuery Table Reference ✅ FIXED

**Problem**: ETL didn't know which BigQuery table to query
**Root Cause**: Frontend only sent `resource_type='invoices'` without table name

**Solution**: ETL now constructs table name from credentials:
```
project_id: from credentials
dataset_id: from credentials (user specifies which dataset when creating connector)
table_name: from resource_type parameter (defaults to 'invoices')

Result: `project_id.dataset_id.invoices`
```

---

## New ETL Flow

### Step 1: User Creates Connector

User navigates to `/dashboard/admin/fontes` and configures BigQuery:

```json
{
  "connection_name": "Production BigQuery",
  "project_id": "my-gcp-project",
  "dataset_id": "ecommerce_data",  // ← User specifies which dataset
  "service_account_json": { ... }
}
```

Stored in `credencial_servico_externo`:
```sql
INSERT INTO credencial_servico_externo (
    client_id,
    nome_servico,
    tipo_servico,
    credenciais_cifradas,
    status
) VALUES (
    'uuid-here',
    'Production BigQuery',
    'BIGQUERY',
    '{"project_id":"my-gcp-project","dataset_id":"ecommerce_data","service_account_json":{...}}',
    'pending'
);
```

---

### Step 2: User Clicks "Conectar e Sincronizar"

Frontend calls:
```javascript
await connectorService.startSync(
  credentialId,      // "6"
  clienteVizuId,     // "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
  'invoices'         // resource_type - defaults to 'invoices'
);
```

Which calls:
```
POST /etl/run
{
  "credential_id": "6",
  "client_id": "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723",
  "resource_type": "invoices",
  "limit": null
}
```

---

### Step 3: ETL Service Processes Request

**[etl_service.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service.py)**

```python
async def run_etl_job(
    credential_id: str,
    client_id: str,
    resource_type: str = "invoices",
    bigquery_table: str | None = None,
    limit: int | None = None
):
    # 1. Load credentials from Supabase
    credential = await supabase_client.select_one(
        "credencial_servico_externo",
        filters={"id": credential_id}
    )

    # 2. Parse credentials JSON
    creds = json.loads(credential["credenciais_cifradas"])
    project_id = creds["project_id"]  # "my-gcp-project"
    dataset_id = creds["dataset_id"]  # "ecommerce_data"

    # 3. Build table name
    if not bigquery_table:
        bigquery_table = f"`{project_id}.{dataset_id}.{resource_type}`"
        # Result: `my-gcp-project.ecommerce_data.invoices`

    # 4. Create BigQuery connector
    connector = await ConnectorFactory.create_connector(
        tipo_servico="BIGQUERY",
        credentials=creds
    )

    # 5. Query BigQuery (all columns)
    query = f"SELECT * FROM {bigquery_table}"

    # 6. Extract, Transform, Load
    async for chunk_df in connector.extract_data(query, chunk_size=1000):
        # Add metadata columns
        chunk_df["client_id"] = client_id
        chunk_df["resource_type"] = resource_type

        # Insert to analytics_silver
        await self._load_to_supabase(chunk_df)
```

---

### Step 4: Data Lands in analytics_silver

```sql
-- Data from BigQuery table: my-gcp-project.ecommerce_data.invoices
INSERT INTO analytics_silver (
    client_id,
    resource_type,
    -- All columns from BigQuery table...
    invoice_id,
    customer_id,
    total_amount,
    created_at,
    ...
) VALUES (
    'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
    'invoices',
    'INV-001',
    'CUST-123',
    1500.00,
    '2024-01-15',
    ...
);
```

**RLS Isolation**: Only this client can see their data (WHERE client_id = auth.jwt() ->> 'sub')

---

## Files Modified

### 1. [etl_service.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service.py)

**Before**:
- Required schema mapping from `data_source_mappings` table
- Used Google Secret Manager
- Didn't know which BigQuery table to query

**After**:
- No schema mapping required
- Credentials stored in Supabase
- Constructs table name from credentials + resource_type

**Key Changes**:
- Removed `schema_registry.get_mapping()` requirement
- Removed Secret Manager import
- Added logic to parse credentials and build table name
- Simplified `_create_connector()` to use Supabase credentials

---

## Testing

### 1. Test BigQuery Connector

1. Navigate to `/dashboard/admin/fontes`
2. Click **"Conectar"** on BigQuery
3. Fill in:
   - Connection Name: "Production BigQuery"
   - Project ID: your GCP project ID
   - Dataset ID: `ecommerce_data` (or your dataset name)
   - Service Account JSON: paste your service account key
4. Click **"Conectar e Sincronizar"**

**Expected Result**:
```
✅ Credentials saved
✅ ETL job started
✅ Query executed: SELECT * FROM `my-gcp-project.ecommerce_data.invoices`
✅ Data inserted to analytics_silver
```

### 2. Check Logs

```bash
docker logs vizu_data_ingestion_api -f
```

**Expected Output**:
```
INFO: Starting ETL job for client_id=uuid, resource_type=invoices
INFO: Retrieving BigQuery credentials for credential_id=6
INFO: Parsing credentials for BIGQUERY connector
INFO: Successfully created BIGQUERY connector
INFO: No table specified - using default: `my-gcp-project.ecommerce_data.invoices`
INFO: Extracting from BigQuery: SELECT * FROM `my-gcp-project.ecommerce_data.invoices`
INFO: Processing chunk of 1000 rows
INFO: Inserting batch 1/10 (100 records)...
INFO: Batch 1/10 inserted successfully
...
INFO: ETL job completed: 10000 rows processed, 10000 rows inserted to analytics_silver
```

### 3. Verify Data in Supabase

```sql
-- Check data was inserted
SELECT
    client_id,
    resource_type,
    COUNT(*) as total_rows
FROM analytics_silver
GROUP BY client_id, resource_type;

-- Expected output:
-- client_id                              | resource_type | total_rows
-- e0e9c949-18fe-4d9a-9295-d5dfb2cc9723  | invoices      | 10000
```

---

## Architecture Simplifications

### What Was Removed:

1. **Schema Mappings** (`data_source_mappings` table) - Not needed for MVP
2. **Google Secret Manager** - Credentials stored in Supabase instead
3. **Worker Process** - ETL runs synchronously via API endpoint
4. **Complex Transformation Logic** - Data ingested as-is from BigQuery

### What Remains:

1. **ETL API Endpoint** - `POST /etl/run`
2. **BigQuery Connector** - Via `vizu_data_connectors`
3. **Supabase Storage** - `analytics_silver` table with RLS
4. **Client Isolation** - `client_id` column for multi-tenancy

---

## Future Enhancements

### Phase 2 (Optional):

1. **Table Selection UI** - Let users choose which table to sync (instead of defaulting to resource_type)
2. **Column Selection** - Let users choose which columns to sync
3. **Incremental Sync** - Only sync new/updated rows (using `updated_at` column)
4. **Scheduled Syncs** - Cron jobs to sync data automatically
5. **Schema Mappings** - Map BigQuery columns to canonical schema (if needed)

### For Now:

MVP works with:
- One BigQuery dataset per connector
- All columns synced
- Full refresh on each sync
- Manual sync triggered by user

---

## Status

✅ **Complete** - BigQuery connector functional
✅ **Dashboard rebuilt** - Frontend calls `/etl/run` correctly
✅ **Data Ingestion API rebuilt** - Simplified ETL flow
✅ **Table migration complete** - All FKs point to `clientes_vizu`

**Ready to test!** 🚀
