# Complete Migration Guide: Consolidate to clientes_vizu

## Summary

This guide consolidates your three overlapping tables into ONE table: `clientes_vizu`.

### Tables Being Consolidated:
1. **`cliente_vizu`** (old, no `external_user_id`) → **WILL BE DROPPED**
2. **`clientes_vizu`** (new, has `external_user_id`) → **KEEP THIS**
3. **`configuracao_negocio`** (legacy config table) → **WILL BE DROPPED**

---

## Issues Fixed

### Issue 1: BigQuery Connector 404 Error ✅ FIXED

**Problem**: Frontend was calling `/ingestion/start` but backend only has `/etl/run`

**Files Modified**:
- [apps/vizu_dashboard/src/services/connectorService.ts](apps/vizu_dashboard/src/services/connectorService.ts#L280-L304)
- [apps/vizu_dashboard/src/components/admin/ConnectorModal.tsx](apps/vizu_dashboard/src/components/admin/ConnectorModal.tsx#L177-L187)

**Changes**:
```typescript
// OLD: Called /ingestion/start with wrong payload
await connectorService.startSync(response.id_credencial, tipoServico, undefined);

// NEW: Calls /etl/run with correct payload
await connectorService.startSync(
  response.id_credencial,
  clienteVizuId,
  'invoices'  // Default resource type for BigQuery
);
```

**Status**: Dashboard rebuilt and restarted ✅

---

### Issue 2: Foreign Key Violation ✅ READY TO FIX

**Problem**: `credencial_servico_externo` has FK to `cliente_vizu` but Google users are in `clientes_vizu`

**Error**:
```
foreign key constraint "credencial_servico_externo_client_id_fkey" violates
Key (client_id)=(e0e9c949-18fe-4d9a-9295-d5dfb2cc9723) is not present in table "cliente_vizu"
```

**Root Cause**: When you log in with Google OAuth, your user record goes to `clientes_vizu`, but the credentials table points to the old `cliente_vizu` table.

**Fix**: Run the SQL migration to update all FKs to point to `clientes_vizu`

---

## Migration Steps

### 1. Code Changes (Already Applied) ✅

**File**: [libs/vizu_models/src/vizu_models/cliente_vizu.py](libs/vizu_models/src/vizu_models/cliente_vizu.py)

**Changes**:
- Changed `__tablename__ = "cliente_vizu"` → `__tablename__ = "clientes_vizu"`
- Added `external_user_id` field for OAuth support
- Added `created_at` and `updated_at` timestamp fields

**File**: [libs/vizu_models/src/vizu_models/credencial_servico_externo.py](libs/vizu_models/src/vizu_models/credencial_servico_externo.py)

**Changes**:
- Changed FK from `foreign_key="cliente_vizu.id"` → `foreign_key="clientes_vizu.id"`

---

### 2. Database Migration (APPLY THIS NOW) ⚠️

**File**: [COMPLETE_TABLE_MIGRATION_TO_CLIENTES_VIZU.sql](COMPLETE_TABLE_MIGRATION_TO_CLIENTES_VIZU.sql)

**What it does**:
1. ✅ Adds missing columns to `clientes_vizu` (`external_user_id`, `created_at`, `updated_at`)
2. ✅ Migrates all data from `cliente_vizu` → `clientes_vizu`
3. ✅ Updates ALL FK constraints to point to `clientes_vizu`:
   - `credencial_servico_externo.client_id`
   - `cliente_final.client_id`
   - `fonte_de_dados.client_id`
   - `conversa.client_id`
4. ✅ Drops legacy tables: `configuracao_negocio`, `cliente_vizu`
5. ✅ Verifies migration success

**How to Apply**:
1. Go to **Supabase Console → SQL Editor**
2. Copy and paste the entire contents of `COMPLETE_TABLE_MIGRATION_TO_CLIENTES_VIZU.sql`
3. Click **"Run"**
4. Review the output to ensure all steps succeeded

---

### 3. Rebuild Services (DO THIS AFTER SQL MIGRATION)

After running the SQL migration, rebuild all services that use the database models:

```bash
# Rebuild all services
docker-compose build atendente_core
docker-compose build analytics_api
docker-compose build data_ingestion_api
docker-compose build file_upload_api
docker-compose build tool_pool_api

# Restart all services
docker-compose up -d
```

---

## What Changes After Migration

### Before Migration:

**Tables**:
- `cliente_vizu` (105+ references in code)
- `clientes_vizu` (15+ references in code)
- `configuracao_negocio` (12+ references in code)

**Foreign Keys**:
- `credencial_servico_externo` → `cliente_vizu` ❌
- `uploaded_files_metadata` → `clientes_vizu` ✅
- `connector_sync_history` → indirect via credencial

**Problem**: Users in different tables depending on how they logged in

---

### After Migration:

**Tables**:
- `clientes_vizu` (ONLY table for clients)

**Foreign Keys**:
- `credencial_servico_externo` → `clientes_vizu` ✅
- `uploaded_files_metadata` → `clientes_vizu` ✅
- `cliente_final` → `clientes_vizu` ✅
- `fonte_de_dados` → `clientes_vizu` ✅
- `conversa` → `clientes_vizu` ✅

**Solution**: All users in ONE table, all FKs point to same table

---

## Table Structure

### clientes_vizu (Final Table)

```sql
CREATE TABLE public.clientes_vizu (
    id                    UUID PRIMARY KEY,
    api_key               TEXT UNIQUE,
    nome_empresa          TEXT NOT NULL,
    tipo_cliente          TEXT,                -- 'freemium' or 'enterprise'
    tier                  TEXT,                -- 'free', 'basic', 'premium', 'enterprise'
    prompt_base           TEXT,
    horario_funcionamento JSONB,
    enabled_tools         TEXT[],              -- Array of tool names
    collection_rag        TEXT,
    external_user_id      TEXT UNIQUE,         -- OAuth user ID (Supabase auth.users.id)
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
```

**Key Features**:
- ✅ Supports both API key authentication and OAuth
- ✅ Has `external_user_id` for RLS policies
- ✅ Has `created_at` and `updated_at` timestamps
- ✅ Consolidates all config fields from `configuracao_negocio`

---

## Testing After Migration

### 1. Test BigQuery Connector Creation

1. Navigate to `/dashboard/admin/fontes`
2. Click **"Conectar"** on BigQuery card
3. Fill in connection details:
   - Connection name: "Test BigQuery"
   - Project ID: your GCP project ID
   - Dataset ID: your dataset name
   - Service Account JSON: paste your service account key
4. Click **"Testar conexão"** → Should show "✅ Conexão testada com sucesso"
5. Click **"Conectar e Sincronizar"**

**Expected**:
- ✅ Credentials save successfully (no FK violation)
- ✅ ETL job starts (no 404 error)
- ✅ Data appears in analytics pages within a few minutes

### 2. Verify Database

```sql
-- Check clientes_vizu has all users
SELECT
    id,
    nome_empresa,
    external_user_id,
    api_key,
    created_at
FROM public.clientes_vizu
ORDER BY created_at DESC;

-- Check credentials reference valid clients
SELECT
    cse.id,
    cse.nome_servico,
    cse.tipo_servico,
    cse.status,
    cv.nome_empresa
FROM public.credencial_servico_externo cse
JOIN public.clientes_vizu cv ON cv.id = cse.client_id;

-- Verify old tables are gone
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('cliente_vizu', 'configuracao_negocio');
-- Should return 0 rows
```

---

## Rollback Plan (If Needed)

If something goes wrong, you can restore from Supabase's automatic backups:

1. Go to **Supabase Dashboard → Database → Backups**
2. Select the backup from before the migration
3. Click **"Restore"**

**Note**: Make sure you have a recent backup before running the migration!

---

## Files Created/Modified

### SQL Scripts:
1. ✅ [COMPLETE_TABLE_MIGRATION_TO_CLIENTES_VIZU.sql](COMPLETE_TABLE_MIGRATION_TO_CLIENTES_VIZU.sql) - Main migration script
2. ✅ [FIX_CREDENCIAL_FK_TO_CLIENTES_VIZU.sql](FIX_CREDENCIAL_FK_TO_CLIENTES_VIZU.sql) - Quick fix (superseded by complete migration)
3. ✅ [TABLE_CONSOLIDATION_ANALYSIS.md](TABLE_CONSOLIDATION_ANALYSIS.md) - Detailed analysis

### Code Changes:
1. ✅ [libs/vizu_models/src/vizu_models/cliente_vizu.py](libs/vizu_models/src/vizu_models/cliente_vizu.py) - Table name and fields
2. ✅ [libs/vizu_models/src/vizu_models/credencial_servico_externo.py](libs/vizu_models/src/vizu_models/credencial_servico_externo.py) - FK update
3. ✅ [apps/vizu_dashboard/src/services/connectorService.ts](apps/vizu_dashboard/src/services/connectorService.ts) - Endpoint fix
4. ✅ [apps/vizu_dashboard/src/components/admin/ConnectorModal.tsx](apps/vizu_dashboard/src/components/admin/ConnectorModal.tsx) - API call fix

---

## Next Steps

1. **APPLY SQL MIGRATION** (run in Supabase Console)
2. **REBUILD SERVICES** (docker-compose build)
3. **TEST BIGQUERY CONNECTOR** (should work now!)
4. **VERIFY DATA** (check clientes_vizu table)

---

## Summary

**Before**: 3 tables, inconsistent data, FK violations, 404 errors
**After**: 1 table, all FKs working, BigQuery connector functional

**Status**: Ready to apply! 🚀
