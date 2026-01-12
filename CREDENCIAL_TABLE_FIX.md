# Fix: Missing credenciais_cifradas Column in credencial_servico_externo Table

## Issue

When trying to save BigQuery connector credentials, the API returns:

```
Failed to create credential for client e0e9c949-18fe-4d9a-9295-d5dfb2cc9723:
{'message': "Could not find the 'credenciais_cifradas' column of 'credencial_servico_externo' in the schema cache", 'code': 'PGRST204'}

INFO: 172.64.149.246:34458 - "POST /credentials/create HTTP/1.1" 500 Internal Server Error
```

**Error Code**: `PGRST204` - PostgREST error indicating column not found in schema cache.

## Root Cause

The `credencial_servico_externo` table is missing the `credenciais_cifradas` column. This column was added in a migration file (`20260105_enhance_credencial_servico_externo.sql`) but the migration **hasn't been applied** to your Supabase database.

## Expected Table Structure

The `credencial_servico_externo` table should have these columns:

| Column Name            | Type         | Description                                    |
|------------------------|--------------|------------------------------------------------|
| id                     | INTEGER      | Primary key (auto-increment)                   |
| client_id        | UUID         | FK to clientes_vizu table                      |
| nome_servico           | TEXT         | Connection name (e.g., "Production BigQuery")  |
| **tipo_servico**       | TEXT         | Service type: BIGQUERY, VTEX, SHOPIFY, etc.    |
| **credenciais_cifradas** | TEXT       | **JSON credentials stored as text**            |
| **status**             | TEXT         | Connection status: pending, active, error      |
| created_at             | TIMESTAMPTZ  | When credential was created                    |
| updated_at             | TIMESTAMPTZ  | Last update timestamp                          |

**Bold columns** = Added by enhancement migration (missing in your database)

## The Migration That Should Have Run

**File**: `supabase/migrations/20260105_enhance_credencial_servico_externo.sql`

```sql
ALTER TABLE credencial_servico_externo
    ADD COLUMN IF NOT EXISTS tipo_servico TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'error', 'pending')),
    ADD COLUMN IF NOT EXISTS credenciais_cifradas TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
```

## Why This Happens

Supabase migrations in the `supabase/migrations/` folder are **not automatically applied** to your Supabase cloud project. You need to:

1. **Local Development**: Use Supabase CLI to apply migrations
2. **Cloud/Production**: Manually run SQL in Supabase SQL Editor

## The Fix

### Option 1: Run SQL Directly (RECOMMENDED)

1. Go to **Supabase Console → SQL Editor**
2. Copy and paste the contents of **[VERIFY_AND_FIX_CREDENCIAL_TABLE.sql](VERIFY_AND_FIX_CREDENCIAL_TABLE.sql)**
3. Click **"Run"**

This script will:
- ✅ Show current table structure
- ✅ Add missing columns if they don't exist
- ✅ Create indexes
- ✅ Set up updated_at trigger
- ✅ Verify the changes

### Option 2: Use Supabase CLI (Alternative)

If you have Supabase CLI installed locally:

```bash
# Link to your Supabase project
supabase link --project-ref <your-project-ref>

# Push migrations
supabase db push
```

## What Gets Created

After running the fix script, your table will have:

### New Columns:
- `tipo_servico` - Stores "BIGQUERY", "VTEX", "SHOPIFY", etc.
- `credenciais_cifradas` - Stores JSON credentials as text
- `status` - Stores "pending", "active", "error", "inactive"
- `created_at` - Auto-set on insert
- `updated_at` - Auto-updated on change

### New Index:
- `idx_credencial_status` - For fast filtering by status

### New Trigger:
- `trigger_credencial_updated_at` - Auto-updates `updated_at` field

## How Credentials Will Be Stored

After the fix, when you save BigQuery credentials:

### Input from Frontend:
```json
{
  "client_id": "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723",
  "nome_conexao": "Production BigQuery",
  "tipo_servico": "BIGQUERY",
  "project_id": "my-gcp-project",
  "dataset_id": "ecommerce_data",
  "service_account_json": {
    "type": "service_account",
    "project_id": "my-gcp-project",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "client_email": "service@project.iam.gserviceaccount.com"
  }
}
```

### Stored in Database:
```sql
INSERT INTO credencial_servico_externo (
    client_id,
    nome_servico,
    tipo_servico,
    credenciais_cifradas,
    status
) VALUES (
    'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
    'Production BigQuery',
    'BIGQUERY',
    '{"project_id":"my-gcp-project","dataset_id":"ecommerce_data","service_account_json":{...}}',
    'pending'
);
```

## Verification Query

After running the fix, verify the table structure:

```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'credencial_servico_externo'
ORDER BY ordinal_position;
```

**Expected Output**:
```
column_name           | data_type                   | is_nullable | column_default
---------------------+-----------------------------+-------------+------------------
id                   | integer                     | NO          | nextval('...')
client_id      | uuid                        | YES         |
nome_servico         | text                        | YES         |
tipo_servico         | text                        | YES         |
status               | text                        | YES         | 'pending'::text
credenciais_cifradas | text                        | YES         |
created_at           | timestamp with time zone    | YES         | now()
updated_at           | timestamp with time zone    | YES         | now()
```

## Testing After Fix

1. Run the SQL fix script in Supabase Console
2. Wait 30 seconds for schema cache to refresh
3. Navigate to `/dashboard/admin/fontes`
4. Click "Conectar" on BigQuery
5. Fill in connection details
6. Click "Conectar e Sincronizar"
7. **Expected**: Credentials save successfully (no more PGRST204 error)

## Check Saved Credentials

After successfully saving:

```sql
SELECT
    id,
    nome_servico,
    tipo_servico,
    status,
    length(credenciais_cifradas) as cred_length,
    created_at
FROM credencial_servico_externo
ORDER BY created_at DESC
LIMIT 5;
```

**Expected Output**:
```
id | nome_servico         | tipo_servico | status  | cred_length | created_at
1  | Production BigQuery  | BIGQUERY     | pending | 1234        | 2026-01-06 15:30:00
```

## Related Migrations

These migrations should all be applied to your Supabase database:

1. **20251230_create_clientes_vizu_table.sql** - Base client table
2. **20260105_enhance_credencial_servico_externo.sql** - Adds columns (THIS ONE IS MISSING)
3. **20260105_create_connector_sync_history.sql** - Sync tracking table
4. **20260105_create_uploaded_files_metadata.sql** - File metadata table

## Files Created

1. [VERIFY_AND_FIX_CREDENCIAL_TABLE.sql](VERIFY_AND_FIX_CREDENCIAL_TABLE.sql) - SQL script to run in Supabase Console
2. [CREDENCIAL_TABLE_FIX.md](CREDENCIAL_TABLE_FIX.md) - This documentation file

---

**Issue**: Missing `credenciais_cifradas` column (PGRST204 error)
**Cause**: Migration not applied to Supabase database
**Fix**: Run SQL script to add missing columns
**Status**: Ready to apply ⚠️
