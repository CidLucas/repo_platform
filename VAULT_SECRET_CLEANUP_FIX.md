# Fix: Vault Secret Cleanup & Server Update

## Problem

Error when creating a new BigQuery connection:
```
Failed to create BigQuery server: duplicate key value violates unique constraint "secrets_name_idx"
```

## Root Cause

The `drop_bigquery_server()` function was **not deleting Vault secrets**. When a user:
1. Creates a connection (adds secret to Vault)
2. Changes parameters and tries to recreate (ETL service calls drop_server)
3. Tries to create again (ETL service calls create_server)

**Step 3 would fail** because the old Vault secret still existed with the same name:
```
v_key_name = 'bigquery_' + client_id + '_sa_key'
```

Vault enforces unique constraint on secret names, so creating a new secret with the same name fails.

## Solution

### 1. Updated `drop_bigquery_server()` to Delete Vault Secrets

**File:** `supabase/migrations/20251219_setup_bigquery_wrapper.sql`

**Changes:**
- Fetch `vault_key_id` when checking for existing server
- Call `vault.delete_secret(v_vault_key_id)` before deleting metadata
- Updated response message to include "Vault secret dropped"

```sql
-- Delete the Vault secret (CRITICAL - prevents duplicate key constraint)
if v_vault_key_id is not null then
  perform vault.delete_secret(v_vault_key_id);
end if;
```

### 2. Updated `create_bigquery_server()` to Allow Updates

**File:** `supabase/migrations/20251219_setup_bigquery_wrapper.sql`

**Changes:**
- Changed from raising exception "BigQuery server already exists" to auto-cleanup
- If server exists, automatically:
  1. Fetch old vault_key_id
  2. Drop the FDW server
  3. Delete the old Vault secret
  4. Delete the metadata
  5. Create new secret and server with new values

```sql
-- Check if server already exists - if so, drop it (user is updating)
if exists (select 1 from public.bigquery_servers where client_id = p_client_id) then
  -- Get old vault key ID
  select vault_key_id into v_existing_vault_key_id
  from public.bigquery_servers
  where client_id = p_client_id;

  -- Drop the server
  execute format(
    'drop server if exists %I cascade',
    v_server_name
  );

  -- Delete the old Vault secret (prevents duplicate key constraint)
  if v_existing_vault_key_id is not null then
    perform vault.delete_secret(v_existing_vault_key_id);
  end if;

  -- Delete metadata
  delete from public.bigquery_servers
  where client_id = p_client_id;
end if;
```

## Impact

### Before This Fix
User flow would fail at step 2:
```
User changes location in frontend
→ ETL service calls drop_server() ✅
→ ETL service calls create_server() ❌ VAULT SECRET CONFLICT
```

### After This Fix
User flow completes successfully:
```
User changes location in frontend
→ ETL service calls drop_server() ✅ (now deletes Vault secret)
→ ETL service calls create_server() ✅ (can create new secret with same name)
```

## Testing

### Test 1: Create New Connection
```bash
# Frontend: Create new BigQuery connector
# Location: US
# Dataset: dataform
# Table: productsinvoices

# Expected: Server created successfully
# Check logs: Should not see "duplicate key" error
```

### Test 2: Update Existing Connection
```bash
# Frontend: Change location from US to EU (or any parameter change)

# Expected:
# - Old server dropped ✅
# - Old Vault secret deleted ✅
# - New server created ✅
# - New Vault secret created ✅
```

### Verify in Database
```sql
-- Check servers exist
select client_id, server_name, location
from public.bigquery_servers;

-- Check Vault secrets (should match servers)
select name from vault.secrets
where name like 'bigquery%';

-- Count should match - one secret per server
```

## Related Files

- `supabase/migrations/20251219_setup_bigquery_wrapper.sql` - Updated functions
- `services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py` - Calls drop_server() when parameters change

## Migrations Applied

✅ Migration 1: `fix_vault_secret_cleanup_and_server_update`
- Updated `create_bigquery_server()` to auto-cleanup existing servers
- Updated `drop_bigquery_server()` to delete Vault secrets

✅ Migration 2: `cleanup_orphaned_vault_secrets`
- Deleted orphaned Vault secrets (secrets without matching servers)
- Result: 0 orphaned secrets remaining

Date: 2026-01-07

## Summary of Changes

| Component | Change | Effect |
|-----------|--------|--------|
| `create_bigquery_server()` | Now auto-drops existing server before creating new one | Users can update connections without manual cleanup |
| `drop_bigquery_server()` | Now deletes Vault secret when dropping server | Prevents duplicate key constraint errors |
| Vault Secrets | Cleaned up orphaned secrets | Database is now consistent |

The fix ensures **automatic cleanup** at every step:
1. User changes parameters → ETL service detects change
2. Drop old server → Vault secret automatically deleted ✅
3. Create new server → New Vault secret created ✅
4. Foreign table created with new values ✅
