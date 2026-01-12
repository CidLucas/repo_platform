# BigQuery FDW Debugging Guide

## Payloads Being Sent

### 1. ETL Service → BigQuery Wrapper Service

```python
# From etl_service_v2.py line ~260
create_foreign_table(
    client_id='e0e9c949_18fe_4d9a_9295_d5dfb2cc9723',  # Sanitized (underscores)
    table_name='productsinvoices',  # User input from credentials
    bigquery_table='productsinvoices',  # User input (just table name)
    columns=[
        {"name": "id_pedido", "type": "text"},
        {"name": "data_transacao", "type": "text"},
        # ... more columns
    ],
    location='US'  # User input from credentials
)
```

### 2. BigQuery Wrapper Service → Supabase RPC

```python
# From bigquery_wrapper_service.py create_foreign_table()
supabase.rpc(
    'create_bigquery_foreign_table',
    {
        'p_client_id': 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723',  # Sanitized
        'p_table_name': 'productsinvoices',  # User table name
        'p_bigquery_table': 'productsinvoices',  # Just table name, NOT fully qualified
        'p_columns': [...],
        'p_location': 'US'  # User location
    }
)
```

### 3. Supabase Migration → Creates Foreign Table

```sql
-- From 20251219_setup_bigquery_wrapper.sql
-- The RPC calls create_bigquery_foreign_table() which:

1. Gets project_id and dataset_id from bigquery_servers table
2. Builds fully-qualified path:
   v_full_bigquery_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || p_bigquery_table || '`'
   -- Result: `analytics-big-query-242119`.`dataform`.`productsinvoices`

3. Wraps in subquery:
   v_table_subquery := '(select * from ' || v_full_bigquery_path || ')'
   -- Result: (select * from `analytics-big-query-242119`.`dataform`.`productsinvoices`)

4. Creates foreign table with subquery + location:
   CREATE FOREIGN TABLE bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_productsinvoices
   (columns...)
   SERVER bigquery_e0e9c949_18fe_4d9a_9295_d5dfb2cc9723
   OPTIONS (
     table '(select * from `analytics-big-query-242119`.`dataform`.`productsinvoices`)',
     location 'US'
   )
```

## Known Issues

### Issue 1: Table Not Found Error
```
Not found: Table analytics-big-query-242119:dataform.productsinvoices
was not found in location US
```

**Root Cause:** Either:
1. The table `productsinvoices` doesn't actually exist in `analytics-big-query-242119:dataform` dataset
2. The table exists but in a different dataset
3. The table exists but the location is different (though `US` should work)

**Verification Steps:**
```bash
# Check BigQuery console or gcloud CLI
gcloud bigquery tables list --dataset_id=dataform --project_id=analytics-big-query-242119

# Or in BigQuery console:
SELECT table_name, table_type
FROM `analytics-big-query-242119.dataform.__TABLES__`
```

### Issue 2: Drop Server JSON Parsing Error
```
Error dropping server: {'message': 'JSON could not be generated', 'code': 200}
```

**Root Cause:** Supabase RPC response contains byte string that's not parsing as JSON

**Fix Applied:** Updated `drop_server()` to handle parsing errors gracefully and check if message contains "dropped"

## Configuration Checklist

✅ No hardcoded defaults:
- ✅ Location: Now comes from user input (removed "southamerica-east1" default)
- ✅ Dataset ID: Now comes from user input
- ✅ Table Name: Now comes from user input
- ✅ Service Account: Stored in Vault

✅ Parameter Change Detection:
- ✅ When location/dataset_id/project_id change, old FDW server is dropped
- ✅ Server is recreated with new values

✅ Logging:
- ✅ Added [PAYLOAD] logs to show what's being sent
- ✅ Added [RESPONSE] logs to show what's returned
- ✅ Added [SUPABASE RPC] logs to track RPC calls

## Testing Steps

1. **Create new BigQuery connection:**
   - Frontend: Select BigQuery, upload Service Account JSON
   - Set Dataset ID: `dataform`
   - Set Table Name: `productsinvoices`
   - Set Location: `US`
   - Click "Connect"

2. **Monitor logs:**
   ```bash
   docker logs vizu_data_ingestion_api -f | grep -E "PAYLOAD|RESPONSE|SUPABASE"
   ```

3. **Verify payloads match expected format**

4. **Check if table exists in BigQuery:**
   - Verify table name: `productsinvoices`
   - Verify dataset: `dataform`
   - Verify project: `analytics-big-query-242119`
   - Verify location: The table's location (not necessarily `US`)

## FDW Documentation Reference

From https://fdw.dev/catalog/bigquery/:

- **Options available:**
  - `table`: Source table name or subquery (required)
  - `location`: Source table location (default: 'US')
  - `timeout`: Query timeout in ms (default: 30000)
  - `rowid_column`: Primary key for modifications

- **Subquery format:**
  ```sql
  table '(select * except(props), to_json_string(props) as props from `my_project.my_dataset.my_table`)'
  ```
  Note: Full qualified table name must be used with subquery

- **Basic example:**
  ```sql
  CREATE FOREIGN TABLE bigquery.people (
    id bigint,
    name text,
    ts timestamp
  )
  SERVER bigquery_server
  OPTIONS (
    table 'people',
    location 'EU'
  );
  ```
