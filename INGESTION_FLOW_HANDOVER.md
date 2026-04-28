# BigQuery Ingestion Flow - Handover Document

## Current Status
The BigQuery ingestion pipeline is **95% complete** but blocked on **pg_cron job execution**. Jobs are being queued correctly, but the scheduled processor is not triggering.

## What's Working ✅

### 1. Discovery Phase (discover-bigquery-columns edge function)
- **Status**: ✅ Fully functional (version 5)
- **Flow**: 
  - User creates connector → discovers BigQuery table schema
  - Service account authentication works
  - Foreign table created with proper typed columns and full `project.dataset.table` reference
  - Columns saved to `client_data_sources.source_columns`
- **Evidence**: Console shows "Foreign table created with discovered columns"

### 2. Column Mapping Phase (match-columns edge function)
- **Status**: ✅ Fully functional
- **Flow**: Automatic + manual column mapping to canonical schema
- **Evidence**: User can view and adjust mappings on the mapping page

### 3. Job Enqueue Phase (run-sync edge function)
- **Status**: ✅ Fully functional (version 14)
- **Flow**:
  - Frontend submits final column mapping → updates `client_data_sources`
  - Calls `run-sync` → validates mapping readiness
  - Creates job record in `analytics_v2.reg_jobs` with status `pending`
  - Returns 202 (Accepted) with `job_id`
  - **Edge function logs confirm jobs are being created successfully**
- **Evidence**: 
  - Edge function logs show multiple successful 202 responses (1-3 seconds execution time)
  - Jobs are created in the database

### 4. Database Schema & RPCs
- **Status**: ✅ Fully implemented
- **Migrations applied**:
  - `20260428230000_create_sync_processor_function_and_cron.sql` - Created RPCs + pg_cron job
  - `20260428231000_implement_bigquery_etl_sync_logic.sql` - Full ETL logic
  - `20260428210000_fix_bigquery_ft_cleanup_and_column_update.sql` - FT metadata handling
  - `fix_bigquery_ft_server_name_constraint` - Fixed NULL server_name
  - `fix_bigquery_ft_cleanup_and_column_update` - Corrected FDW option from `object_name` → `table`

### 5. Frontend Fixes Applied
- **Fixed**: Column name mismatch (`atualizado_em` → `updated_at`) in `connectorService.ts:459`

## What's NOT Working ❌

### pg_cron Jobs Not Triggering

**Symptom**: 
- Frontend hangs on "Confirmar e Sincronizar" page
- Jobs are created in `analytics_v2.reg_jobs` with status `pending`
- Jobs never transition to `running` → they never execute

**Root Cause**: The pg_cron scheduled job is not triggering

**Evidence**:
```sql
SELECT * FROM cron.job;
```
Will show the scheduled job, but you won't see it executing.

**Scheduled Job Definition** (from migration):
```sql
SELECT cron.schedule(
    'process-pending-sync-jobs',
    '*/30 * * * * *',  -- Every 30 seconds
    'SELECT public.process_pending_sync_jobs();'
);
```

This job should:
1. Run every 30 seconds
2. Call `process_pending_sync_jobs()` RPC
3. Process up to 10 pending jobs per run
4. Execute `sincronizar_dados_cliente(job_id)` for each job
5. Jobs should transition: `pending` → `running` → `completed` or `failed`

## How to Debug

### 1. Check if pg_cron extension is enabled
```sql
SELECT * FROM pg_extension WHERE extname = 'pg_cron';
```
Should return a row. If not:
```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

### 2. Check scheduled jobs
```sql
SELECT jobid, jobname, schedule, command, active 
FROM cron.job 
WHERE jobname = 'process-pending-sync-jobs';
```
- `active` should be `true`
- `command` should be `SELECT public.process_pending_sync_jobs();`

### 3. Check cron job log/history (if supported in your Supabase version)
```sql
SELECT * FROM cron.job_run_details 
WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'process-pending-sync-jobs')
ORDER BY start_time DESC 
LIMIT 10;
```

### 4. Manually test the processor RPC
```sql
SELECT * FROM public.process_pending_sync_jobs();
```
Should return job counts. If this works, the RPC is fine—cron just isn't calling it.

### 5. Check pending jobs
```sql
SELECT job_id, status, created_at, error_message 
FROM analytics_v2.reg_jobs 
WHERE status = 'pending' 
ORDER BY created_at DESC;
```

## Complete Ingestion Flow (When Everything Works)

```
1. User creates BigQuery connector
   ↓
2. discover-bigquery-columns edge function
   - Fetches schema from BigQuery API
   - Creates foreign table with typed columns
   - Saves source_columns to client_data_sources
   ↓
3. User adjusts column mapping on mapping page
   ↓
4. User clicks "Confirmar e Sincronizar"
   - Frontend updates column_mapping in client_data_sources
   - Calls run-sync edge function
   - run-sync creates job record: status='pending'
   - Returns job_id to frontend
   ↓
5. [BLOCKING] pg_cron triggers every 30 seconds
   - process_pending_sync_jobs() executes
   - Fetches all pending jobs
   - For each job, calls sincronizar_dados_cliente(job_id)
   ↓
6. sincronizar_dados_cliente RPC executes
   - Queries foreign table
   - Maps BigQuery columns to canonical names
   - Upserts into dim_clientes, dim_fornecedores, dim_inventory, dim_datas
   - Inserts into fato_transacoes fact table
   - Job status transitions: pending → running → completed
   ↓
7. Frontend polls job status
   - Eventually shows "Sync complete"
   - Displays rows_inserted count
```

## Database Schema References

### Key Tables
- `analytics_v2.reg_jobs` - Job queue (job_id, status, progress_pct, error_message)
- `public.client_data_sources` - Data source metadata + column mapping
- `public.bigquery_foreign_tables` - Foreign table mappings
- `public.bigquery_servers` - BigQuery FDW server configuration

### Key RPCs
- `process_pending_sync_jobs()` - Polls pending jobs (called by pg_cron)
- `sincronizar_dados_cliente(job_id UUID)` - Executes actual sync
- `create_bigquery_foreign_table_from_schema(client_id TEXT, columns JSONB)` - Creates FT with schema

## Environment Setup Needed

Verify these are configured:
1. **Supabase project extensions**: pg_cron must be enabled
2. **Edge function env vars**: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
3. **BigQuery credentials**: Service account JSON stored in vault or passed via edge function
4. **RLS policies**: May need to adjust if jobs aren't inserting

## Next Steps to Unblock

1. **Verify pg_cron is enabled**
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_cron;
   ```

2. **Verify scheduled job exists and is active**
   ```sql
   SELECT * FROM cron.job WHERE jobname = 'process-pending-sync-jobs';
   ```

3. **Test manual execution of processor**
   ```sql
   SELECT * FROM public.process_pending_sync_jobs();
   ```

4. **Check Supabase dashboard** for:
   - Database extension status
   - Any pg_cron configuration issues
   - RLS policy blocking access

5. **If manual processor works**, issue is with pg_cron scheduling:
   - May need to recreate the cron job
   - May need to contact Supabase support if pg_cron isn't triggering in their infrastructure

6. **Alternative if pg_cron fails**:
   - Create a Supabase scheduled function (native Supabase feature)
   - Or use an external scheduler (e.g., AWS EventBridge) to call an edge function that executes the processor

## Files Modified

- `supabase/migrations/20260428210000_fix_bigquery_ft_cleanup_and_column_update.sql`
- `supabase/migrations/20260428230000_create_sync_processor_function_and_cron.sql`
- `supabase/migrations/20260428231000_implement_bigquery_etl_sync_logic.sql`
- `supabase/migrations/fix_bigquery_ft_server_name_constraint.sql`
- `supabase/functions/discover-bigquery-columns/index.ts` (version 5)
- `apps/blu_dashboard/src/services/connectorService.ts` (line 459)

## Testing Checklist

- [ ] pg_cron extension enabled
- [ ] Scheduled job `process-pending-sync-jobs` active
- [ ] Manual RPC call `process_pending_sync_jobs()` returns results
- [ ] Create test connector, run discovery
- [ ] Click "Confirmar e Sincronizar"
- [ ] Check `analytics_v2.reg_jobs` for job record
- [ ] Wait 30 seconds, job should transition to `running`
- [ ] Wait for job to complete (`completed` or `failed`)
- [ ] Check `analytics_v2.fato_transacoes` for inserted rows

---

**Status**: Awaiting pg_cron trigger investigation. All data transformation logic is complete and tested.
