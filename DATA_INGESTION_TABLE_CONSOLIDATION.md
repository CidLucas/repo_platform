# Data Ingestion Table Consolidation Analysis

## Overview

After reviewing [table_details.sql](table_details.sql), I've identified significant overlap between legacy and new data ingestion tables. This analysis follows the same approach used to consolidate `cliente_vizu`, `clientes_vizu`, and `configuracao_negocio`.

---

## Critical Overlaps Identified

### 1. **Credential Storage Duplication** ⚠️ HIGH PRIORITY

**Two tables storing the same data:**

#### `credencial_servico_externo` (Currently in use by ETL)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       integer      NO       (PRIMARY KEY)
client_id          uuid         NO
nome_servico             varchar      NO
tipo_servico             text         YES
status                   text         YES
credenciais_cifradas     text         YES
created_at               timestamptz  YES
updated_at               timestamptz  YES
```

#### `data_source_credentials` (Appears unused)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO       (PRIMARY KEY)
client_id          varchar      NO
nome_conexao             varchar      NO
tipo_servico             varchar      NO
secret_manager_id        varchar      YES
status                   varchar      YES
connection_metadata      jsonb        YES
last_sync_at             timestamptz  YES
created_at               timestamptz  YES
updated_at               timestamptz  YES
```

**Analysis:**
- Both store external service credentials (BigQuery, VTEX, etc.)
- Both have: `client_id`, `tipo_servico`, `status`, `created_at`, `updated_at`
- `credencial_servico_externo` uses `credenciais_cifradas` (text JSON)
- `data_source_credentials` uses `secret_manager_id` + `connection_metadata` (jsonb)
- **Current ETL V2 uses `credencial_servico_externo`** (see [etl_service_v2.py:64](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L64))
- `data_source_credentials` appears to be an unused duplicate

**Type Inconsistencies:**
- `credencial_servico_externo.id` is `integer`
- `data_source_credentials.id` is `uuid`
- `credencial_servico_externo.client_id` is `uuid`
- `data_source_credentials.client_id` is `varchar`

**Recommendation:** **Keep `credencial_servico_externo`**, drop `data_source_credentials`

---

### 2. **Data Source Mapping Duplication** ⚠️ HIGH PRIORITY

**Two tables tracking data source mappings:**

#### `client_data_sources` (NEW - created in migration 20260106)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
client_id                text         NO
source_type              text         NO       ('bigquery', 'csv', 'vtex')
resource_type            text         NO       ('invoices', 'products')
storage_type             text         NO       ('foreign_table', 'jsonb_table')
storage_location         text         NO       (table name or path)
column_mapping           jsonb        YES
last_synced_at           timestamptz  YES
sync_status              text         YES
error_message            text         YES
created_at               timestamptz  YES
updated_at               timestamptz  YES
```

#### `data_source_mappings` (Legacy - appears unused)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
credential_id            uuid         NO
client_id          varchar      NO
source_type              varchar      NO
source_resource          varchar      NO
source_table_full_name   varchar      YES
source_columns           jsonb        NO
source_sample_data       jsonb        YES
column_mapping           jsonb        NO
unmapped_columns         jsonb        YES
ignored_columns          jsonb        YES
match_confidence         jsonb        YES
status                   varchar      YES
is_auto_generated        boolean      YES
reviewed_by              varchar      YES
reviewed_at              timestamptz  YES
created_at               timestamptz  YES
updated_at               timestamptz  YES
```

**Analysis:**
- Both track data source metadata and column mappings
- Both have: `column_mapping`, `source_type`, `status`, `created_at`, `updated_at`
- `client_data_sources` is simpler, focused on storage location
- `data_source_mappings` has more detailed mapping metadata (unmapped_columns, match_confidence, reviewed status)
- **`client_data_sources` is being used by ETL V2** (see [etl_service_v2.py:163](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L163))
- `data_source_mappings` appears unused in current codebase

**Key Difference:**
- `data_source_mappings` has `credential_id` FK (links to credentials table)
- `client_data_sources` does NOT have `credential_id` (missing FK)

**Recommendation:** **Keep `client_data_sources`** (newer, simpler), **add missing fields** from `data_source_mappings`, then drop legacy table

---

### 3. **Job/Sync History Duplication** ⚠️ MEDIUM PRIORITY

**Two tables tracking sync/job history:**

#### `connector_sync_history` (NEW - created in migration 20260105)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
credential_id            integer      NO       (FK type mismatch!)
status                   text         NO
sync_started_at          timestamptz  NO
sync_completed_at        timestamptz  YES
duration_seconds         integer      YES
records_processed        integer      YES
records_inserted         integer      YES
records_updated          integer      YES
records_failed           integer      YES
resource_type            text         YES
error_message            text         YES
created_at               timestamptz  NO
updated_at               timestamptz  NO
```

#### `ingestion_jobs` (Legacy - appears unused)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
credential_id            uuid         NO       (FK type mismatch!)
mapping_id               uuid         YES
client_id          varchar      NO
job_id                   varchar      NO
pubsub_message_id        varchar      YES
source_resource          varchar      NO
target_table             varchar      YES
status                   varchar      YES
progress_percent         integer      YES
records_extracted        integer      YES
records_loaded           integer      YES
error_message            text         YES
error_details            jsonb        YES
started_at               timestamptz  YES
completed_at             timestamptz  YES
created_at               timestamptz  YES
updated_at               timestamptz  YES
```

**Analysis:**
- Both track sync/ingestion job history with status and metrics
- Both have: `status`, `error_message`, `started_at`, `completed_at`, `created_at`, `updated_at`
- **Critical FK type mismatch**:
  - `connector_sync_history.credential_id` is `integer` (matches `credencial_servico_externo.id`)
  - `ingestion_jobs.credential_id` is `uuid` (does NOT match any credential table!)
- `connector_sync_history` is simpler, focused on sync metrics
- `ingestion_jobs` has more ETL metadata (`mapping_id`, `pubsub_message_id`, `target_table`)
- Neither appears actively used in current ETL V2 code

**Recommendation:** **Keep `connector_sync_history`** (correct FK type), **add useful fields** from `ingestion_jobs`, drop legacy table

---

### 4. **Integration Tables** ✅ OK TO KEEP

#### `integration_configs`
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
client_id          uuid         NO
provider                 text         YES       ('shopify', 'vtex', etc.)
config_type              text         YES
client_id_encrypted      text         YES       (OAuth client ID)
client_secret_encrypted  text         YES       (OAuth client secret)
redirect_uri             text         YES
scopes                   jsonb        YES
created_at               timestamptz  YES
updated_at               timestamptz  YES
```

#### `integration_tokens`
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
client_id          uuid         NO
provider                 text         YES
access_token_encrypted   text         YES
refresh_token_encrypted  text         YES
token_type               text         YES
expires_at               timestamptz  YES
scopes                   jsonb        YES
metadata                 jsonb        YES
created_at               timestamptz  YES
```

**Analysis:**
- These are specifically for **OAuth-based integrations** (Shopify, VTEX OAuth flow)
- Different from **service account credentials** (BigQuery, API keys)
- No overlap with credential or mapping tables
- **Recommendation:** **Keep both tables as-is** - they serve a different purpose

---

### 5. **Raw Data Storage** ✅ OK TO KEEP

#### `raw_data_jsonb` (NEW - created in migration 20260106)
```
Column Name              Type         Nullable
-----------------        --------     --------
id                       uuid         NO
client_id                text         NO
source_type              text         NO
resource_type            text         NO
raw_data                 jsonb        NO       (flexible CSV/API storage)
source_file              text         YES
row_number               integer      YES
created_at               timestamptz  YES
```

**Analysis:**
- Flexible JSONB storage for CSV/VTEX/API data
- No overlap with other tables (unique purpose)
- **Recommendation:** **Keep as-is**

---

## Proposed Consolidation Plan

### Phase 1: Enhance and Keep `credencial_servico_externo`

**Current State:** Already in use by ETL V2

**Add Missing Fields** from `data_source_credentials`:
```sql
ALTER TABLE credencial_servico_externo
  ADD COLUMN IF NOT EXISTS connection_metadata JSONB,
  ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;

COMMENT ON COLUMN credencial_servico_externo.connection_metadata IS
  'Additional connection settings (project_id, dataset_id, table_name, etc.)';

COMMENT ON COLUMN credencial_servico_externo.last_sync_at IS
  'Timestamp of last successful sync for this credential';
```

**Migrate Data** (if any exists in `data_source_credentials`):
```sql
-- Check if any data exists first
SELECT COUNT(*) FROM data_source_credentials;

-- If data exists, migrate it
INSERT INTO credencial_servico_externo (
  client_id,
  nome_servico,
  tipo_servico,
  status,
  credenciais_cifradas,
  connection_metadata,
  last_sync_at,
  created_at,
  updated_at
)
SELECT
  client_id::uuid,
  nome_conexao,
  tipo_servico,
  status,
  COALESCE(connection_metadata::text, '{}'),  -- Store as text JSON
  connection_metadata,
  last_sync_at,
  created_at,
  updated_at
FROM data_source_credentials
WHERE NOT EXISTS (
  SELECT 1 FROM credencial_servico_externo cse
  WHERE cse.client_id = data_source_credentials.client_id::uuid
    AND cse.tipo_servico = data_source_credentials.tipo_servico
);
```

**Drop Legacy Table:**
```sql
DROP TABLE IF EXISTS data_source_credentials CASCADE;
```

---

### Phase 2: Enhance and Keep `client_data_sources`

**Current State:** Created recently, used by ETL V2

**Add Missing FK and Useful Fields** from `data_source_mappings`:
```sql
ALTER TABLE client_data_sources
  ADD COLUMN IF NOT EXISTS credential_id INTEGER REFERENCES credencial_servico_externo(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS source_columns JSONB,
  ADD COLUMN IF NOT EXISTS source_sample_data JSONB,
  ADD COLUMN IF NOT EXISTS unmapped_columns JSONB,
  ADD COLUMN IF NOT EXISTS ignored_columns JSONB,
  ADD COLUMN IF NOT EXISTS match_confidence JSONB,
  ADD COLUMN IF NOT EXISTS is_auto_generated BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS reviewed_by TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_client_data_sources_credential_id
  ON client_data_sources(credential_id);

COMMENT ON COLUMN client_data_sources.credential_id IS
  'FK to credencial_servico_externo - which credential created this data source';

COMMENT ON COLUMN client_data_sources.source_columns IS
  'Original column schema from source (BigQuery INFORMATION_SCHEMA, CSV headers, etc.)';

COMMENT ON COLUMN client_data_sources.source_sample_data IS
  'Sample rows from source for preview and type inference';

COMMENT ON COLUMN client_data_sources.unmapped_columns IS
  'Source columns that could not be automatically mapped to canonical schema';

COMMENT ON COLUMN client_data_sources.ignored_columns IS
  'Source columns explicitly ignored by user';

COMMENT ON COLUMN client_data_sources.match_confidence IS
  'AI-generated confidence scores for automatic column mapping';

COMMENT ON COLUMN client_data_sources.is_auto_generated IS
  'Whether mapping was auto-generated or manually configured';

COMMENT ON COLUMN client_data_sources.reviewed_by IS
  'User ID who reviewed/approved the mapping';

COMMENT ON COLUMN client_data_sources.reviewed_at IS
  'When the mapping was last reviewed';
```

**Migrate Data** (if any exists in `data_source_mappings`):
```sql
-- Check if any data exists first
SELECT COUNT(*) FROM data_source_mappings;

-- If data exists, migrate it
-- NOTE: Need to match credential_id (uuid → integer conversion)
INSERT INTO client_data_sources (
  client_id,
  source_type,
  resource_type,
  storage_type,
  storage_location,
  column_mapping,
  credential_id,
  source_columns,
  source_sample_data,
  unmapped_columns,
  ignored_columns,
  match_confidence,
  sync_status,
  is_auto_generated,
  reviewed_by,
  reviewed_at,
  created_at,
  updated_at
)
SELECT
  dsm.client_id,
  dsm.source_type,
  dsm.source_resource,
  'unknown',  -- Storage type not in legacy table
  COALESCE(dsm.source_table_full_name, ''),
  dsm.column_mapping,
  (SELECT cse.id FROM credencial_servico_externo cse
   WHERE cse.client_id::text = dsm.client_id
     AND cse.tipo_servico = dsm.source_type
   LIMIT 1) as credential_id,
  dsm.source_columns,
  dsm.source_sample_data,
  dsm.unmapped_columns,
  dsm.ignored_columns,
  dsm.match_confidence,
  dsm.status,
  dsm.is_auto_generated,
  dsm.reviewed_by,
  dsm.reviewed_at,
  dsm.created_at,
  dsm.updated_at
FROM data_source_mappings dsm
WHERE NOT EXISTS (
  SELECT 1 FROM client_data_sources cds
  WHERE cds.client_id = dsm.client_id
    AND cds.source_type = dsm.source_type
    AND cds.resource_type = dsm.source_resource
);
```

**Drop Legacy Table:**
```sql
DROP TABLE IF EXISTS data_source_mappings CASCADE;
```

---

### Phase 3: Enhance and Keep `connector_sync_history`

**Current State:** Created recently, correct FK type

**Add Useful Fields** from `ingestion_jobs`:
```sql
ALTER TABLE connector_sync_history
  ADD COLUMN IF NOT EXISTS client_id UUID,
  ADD COLUMN IF NOT EXISTS job_id TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS mapping_id UUID,
  ADD COLUMN IF NOT EXISTS target_table TEXT,
  ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS error_details JSONB;

CREATE INDEX IF NOT EXISTS idx_connector_sync_history_job_id
  ON connector_sync_history(job_id);

CREATE INDEX IF NOT EXISTS idx_connector_sync_history_client_id
  ON connector_sync_history(client_id);

COMMENT ON COLUMN connector_sync_history.client_id IS
  'Redundant with credential FK but useful for queries';

COMMENT ON COLUMN connector_sync_history.job_id IS
  'Unique job identifier for tracking across services';

COMMENT ON COLUMN connector_sync_history.mapping_id IS
  'FK to client_data_sources - which mapping was used';

COMMENT ON COLUMN connector_sync_history.target_table IS
  'Destination table name (foreign_table, gold table, etc.)';

COMMENT ON COLUMN connector_sync_history.progress_percent IS
  'Current progress percentage (0-100) for in-progress jobs';

COMMENT ON COLUMN connector_sync_history.error_details IS
  'Detailed error information (stack trace, BigQuery error, etc.)';
```

**Migrate Data** (if any exists in `ingestion_jobs`):
```sql
-- Check if any data exists first
SELECT COUNT(*) FROM ingestion_jobs;

-- If data exists, migrate it
-- NOTE: Need to map UUID credential_id → integer credential_id
INSERT INTO connector_sync_history (
  credential_id,
  client_id,
  status,
  sync_started_at,
  sync_completed_at,
  duration_seconds,
  records_processed,
  records_inserted,
  resource_type,
  error_message,
  job_id,
  mapping_id,
  target_table,
  progress_percent,
  error_details,
  created_at,
  updated_at
)
SELECT
  (SELECT cse.id FROM credencial_servico_externo cse
   WHERE cse.client_id::text = ij.client_id
   LIMIT 1) as credential_id,
  ij.client_id::uuid,
  ij.status,
  ij.started_at,
  ij.completed_at,
  EXTRACT(EPOCH FROM (ij.completed_at - ij.started_at))::integer as duration_seconds,
  COALESCE(ij.records_extracted, 0) + COALESCE(ij.records_loaded, 0) as records_processed,
  COALESCE(ij.records_loaded, 0) as records_inserted,
  ij.source_resource,
  ij.error_message,
  ij.job_id,
  ij.mapping_id,
  ij.target_table,
  ij.progress_percent,
  ij.error_details,
  ij.created_at,
  ij.updated_at
FROM ingestion_jobs ij
WHERE NOT EXISTS (
  SELECT 1 FROM connector_sync_history csh
  WHERE csh.job_id = ij.job_id
);
```

**Drop Legacy Table:**
```sql
DROP TABLE IF EXISTS ingestion_jobs CASCADE;
```

---

## Final Consolidated Schema

After consolidation, we'll have **6 tables** instead of **9**:

### Core Data Ingestion Tables (Enhanced)
1. **`credencial_servico_externo`** ✅
   - All external service credentials (BigQuery, VTEX, CSV connectors)
   - Added: `connection_metadata`, `last_sync_at`

2. **`client_data_sources`** ✅
   - Registry of all data sources with storage location
   - Added: `credential_id` FK, `source_columns`, `unmapped_columns`, `match_confidence`, review fields

3. **`connector_sync_history`** ✅
   - Complete sync/job history with metrics
   - Added: `job_id`, `mapping_id`, `target_table`, `progress_percent`, `error_details`

4. **`raw_data_jsonb`** ✅
   - Temporary JSONB storage for CSV/API data
   - No changes needed

### OAuth/Integration Tables (Keep Separate)
5. **`integration_configs`** ✅ - OAuth app configurations
6. **`integration_tokens`** ✅ - OAuth access/refresh tokens

### Tables to Drop ❌
- ❌ `data_source_credentials` (merged into `credencial_servico_externo`)
- ❌ `data_source_mappings` (merged into `client_data_sources`)
- ❌ `ingestion_jobs` (merged into `connector_sync_history`)

---

## Benefits

1. **Reduced complexity** - 3 fewer tables to maintain (9 → 6)
2. **No FK type conflicts** - All FKs properly typed (`credential_id` as `integer`)
3. **Clear separation** - Service account credentials vs OAuth credentials
4. **Backward compatible** - Can migrate existing data safely
5. **Matches current usage** - ETL V2 already uses `credencial_servico_externo` and `client_data_sources`
6. **Better observability** - Enhanced history tracking with `job_id`, `error_details`, etc.

---

## Implementation Order

1. ✅ **Backup all tables** - Export data before any changes
2. ✅ **Phase 1: Enhance `credencial_servico_externo`** - Add columns, migrate data, drop legacy
3. ✅ **Phase 2: Enhance `client_data_sources`** - Add FK and columns, migrate data, drop legacy
4. ✅ **Phase 3: Enhance `connector_sync_history`** - Add columns, migrate data, drop legacy
5. ✅ **Update ETL Service** - Use enhanced fields (`credential_id` in `client_data_sources`)
6. ✅ **Update Analytics API** - Query consolidated tables
7. ✅ **Test thoroughly** - Verify all data flows work
8. ✅ **Monitor production** - Watch for any FK violations or missing data

---

## SQL Migration File

I'll create a complete migration file: `supabase/migrations/20260106_consolidate_data_ingestion_tables.sql`

This migration will:
- Enhance the 3 core tables
- Migrate data from legacy tables (if any exists)
- Drop legacy tables
- Update RLS policies
- Grant permissions

---

## Next Steps

Ready to create the SQL migration file?
