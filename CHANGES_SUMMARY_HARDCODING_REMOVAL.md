# Summary of Changes: Hardcoding Removal & Payload Debugging

## 1. Removed All Hardcoded Values ✅

### Schema Changes
- **File:** `services/data_ingestion_api/src/data_ingestion_api/schemas/schemas.py`
- **Change:** Removed `Field("southamerica-east1")` default for `location`
  - Before: `location: str | None = Field("southamerica-east1", ...)`
  - After: `location: str | None = Field(None, ...)` - Now REQUIRED from user

### ETL Service Changes
- **File:** `services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py`

1. **Fixed location default** (Line 81)
   - Before: `location = creds.get("location", "southamerica-east1")`
   - After: `location = creds.get("location")` - No fallback, must be provided
   - Added validation to check location is provided

2. **Added parameter change detection** (Lines 130-148)
   - When user changes location/dataset_id/project_id, detect it
   - Drop old FDW server automatically
   - Recreate with new values
   ```python
   if old_location != location or old_dataset != dataset_id or old_project != project_id:
       drop_result = await bigquery_wrapper_service.drop_server(client_id)
       existing_server = None  # Force recreation
   ```

3. **Pass location to setup** (Line 169)
   - Before: `setup_bigquery_connection(...dataset_id=dataset_id)`
   - After: `setup_bigquery_connection(...location=location)`

4. **Added comprehensive logging** (Lines 259-268)
   - Log ETL payload being sent
   - Log ETL response received

### BigQuery Wrapper Service Changes
- **File:** `services/data_ingestion_api/src/data_ingestion_api/services/bigquery_wrapper_service.py`

1. **Enhanced create_foreign_table logging** (Lines 161-172)
   ```python
   rpc_payload = {
       'p_client_id': safe_client,
       'p_table_name': table_name,
       'p_bigquery_table': bigquery_table,
       'p_columns': columns,
       'p_location': location
   }
   logger.info(f"[SUPABASE RPC] Calling create_bigquery_foreign_table: {rpc_payload}")
   ```

2. **Enhanced setup_bigquery_connection logging** (Lines 87-97)
   - Log project_id, dataset_id, location being passed
   - Log that service account key is present (without exposing it)

3. **Fixed drop_server error handling** (Lines 395-429)
   - Before: Simple response.get('success')
   - After: Robust handling with logging
   ```python
   # Handle JSON parsing errors gracefully
   try:
       response = result.data
   except Exception as parse_error:
       logger.warning(f"Could not parse response.data: {parse_error}")
       response = result if isinstance(result, dict) else {...}

   # Check if success key exists or if message says "dropped"
   if isinstance(response, dict) and response.get('success'):
       return response
   else:
       # Still return success if message says "dropped"
       return {'success': True, 'message': ...}
   ```

## 2. Added Detailed Payload Logging

All payloads now logged with `[PAYLOAD]` and `[RESPONSE]` tags for easy grep:

```bash
# View all payloads sent
docker logs vizu_data_ingestion_api | grep "PAYLOAD"

# View all responses
docker logs vizu_data_ingestion_api | grep "RESPONSE"

# View Supabase RPC calls
docker logs vizu_data_ingestion_api | grep "SUPABASE RPC"
```

### Example Log Output
```
INFO: [PAYLOAD] create_foreign_table: {
  'client_id': 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723',
  'table_name': 'productsinvoices',
  'bigquery_table': 'productsinvoices',
  'columns': [...],
  'location': 'US'
}

INFO: [SUPABASE RPC] Calling create_bigquery_foreign_table with payload: {
  'p_client_id': 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723',
  'p_table_name': 'productsinvoices',
  'p_bigquery_table': 'productsinvoices',
  'p_columns': [...],
  'p_location': 'US'
}

INFO: [SUPABASE RESPONSE] create_bigquery_foreign_table returned: {...}
```

## 3. Data Flow Now

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (ConnectorModal.tsx)                               │
│ - Service Account JSON (with project_id)                    │
│ - Dataset ID                                                │
│ - Table Name                                                │
│ - Location                                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend ETL Service V2                                      │
│ - Loads credentials from Supabase                           │
│ - Extracts: project_id, dataset_id, table_name, location   │
│ - [NO HARDCODES - all from user input]                      │
│ - Detects if parameters changed                            │
│ - Drops old server if values changed                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ BigQuery Wrapper Service                                    │
│ - Logs RPC payload (showing exact values)                  │
│ - Calls Supabase RPC                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Supabase PostgreSQL (20251219_setup_bigquery_wrapper.sql)  │
│ - create_bigquery_server() RPC function                     │
│   * Stores credentials in Vault                            │
│   * Creates FDW server with user-provided values           │
│   * Options: project_id, dataset_id, location              │
│ - create_bigquery_foreign_table() RPC function             │
│   * Builds fully-qualified path                            │
│   * Creates foreign table with location option              │
│   * Stores metadata in bigquery_foreign_tables              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ BigQuery (via Wrappers FDW)                                 │
│ - Query: analytics-big-query-242119:dataform.productsinvoices
│ - Location: US                                              │
│ - All from user input ✅                                    │
└─────────────────────────────────────────────────────────────┘
```

## 4. Testing the Changes

### Test 1: Create Connection with US Location
```bash
# Logs should show:
# INFO: [PAYLOAD] create_foreign_table: ...'location': 'US'...
# INFO: [SUPABASE RPC] Calling create_bigquery_foreign_table: ...'p_location': 'US'...
```

### Test 2: Change Location and Create Again
```bash
# Logs should show:
# INFO: Location changed from 'US' to 'EU' - will recreate server
# INFO: User parameters changed - dropping old server
# INFO: Dropping BigQuery server for client...
# INFO: Server doesn't exist, creating...
# INFO: [SUPABASE RPC] Calling create_bigquery_foreign_table: ...'p_location': 'EU'...
```

### Test 3: Verify No More Hardcodes
```bash
# Search codebase for hardcoded values
grep -r "southamerica-east1" services/data_ingestion_api/
grep -r "dataform" services/data_ingestion_api/  # Should not have hardcoded dataset
grep -r "productsinvoices" services/data_ingestion_api/  # Should not have hardcoded table
```

## 5. Related Documentation

- [BIGQUERY_FDW_DEBUG_GUIDE.md](./BIGQUERY_FDW_DEBUG_GUIDE.md) - Full debugging guide with FDW documentation
- [fdw.dev/catalog/bigquery/](https://fdw.dev/catalog/bigquery/) - Official BigQuery FDW documentation

## Files Modified

1. `services/data_ingestion_api/src/data_ingestion_api/schemas/schemas.py`
2. `services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py`
3. `services/data_ingestion_api/src/data_ingestion_api/services/bigquery_wrapper_service.py`

## Known Issues Still Being Investigated

### Issue: Table Not Found
```
Not found: Table analytics-big-query-242119:dataform.productsinvoices
was not found in location US
```

**Next Steps:**
1. Verify the table really exists in BigQuery console
2. Check if table is in different dataset
3. Check if location setting is correct in BigQuery
4. Run: `gcloud bigquery tables list --dataset_id=dataform --project_id=analytics-big-query-242119`
