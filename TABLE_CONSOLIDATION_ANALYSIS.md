# Table Consolidation Analysis: cliente_vizu vs clientes_vizu

## Current Problem

**Error**: `foreign key constraint "credencial_servico_externo_client_id_fkey" violates`

**Root Cause**:
- Google OAuth users are stored in `clientes_vizu` table (new, with `external_user_id`)
- `credencial_servico_externo` has a FK to `cliente_vizu` table (old, without `external_user_id`)
- When trying to save credentials for a Google user, the FK fails because the user doesn't exist in the old table

## Table Structure Comparison

### `cliente_vizu` (OLD TABLE - Alembic/PostgreSQL)
```
id                    uuid              PRIMARY KEY
nome_empresa          varchar           NOT NULL
tipo_cliente          ENUM              (freemium/enterprise)
tier                  ENUM              (free/basic/premium/enterprise)
api_key               varchar
horario_funcionamento jsonb             (merged from configuracao_negocio)
prompt_base           text              (merged from configuracao_negocio)
collection_rag        text              (merged from configuracao_negocio)
enabled_tools         jsonb             (merged from configuracao_negocio)
```

**Missing**: `external_user_id`, `created_at`, `updated_at`

**Used by**: All legacy services via Alembic migrations, SQLModel ORM

### `clientes_vizu` (NEW TABLE - Supabase/Multi-tenant)
```
id                    uuid              PRIMARY KEY
api_key               text
nome_empresa          text              NOT NULL
tipo_cliente          text              (freemium/enterprise)
tier                  text              (free/basic/premium/enterprise)
prompt_base           text
horario_funcionamento jsonb
enabled_tools         text[]            (ARRAY instead of jsonb)
collection_rag        text
external_user_id      text              ← KEY DIFFERENCE (for OAuth/RLS)
created_at            timestamptz
updated_at            timestamptz
```

**Used by**: Supabase RLS, OAuth authentication, new services

### `configuracao_negocio` (LEGACY - Being Merged)
```
id                    integer           PRIMARY KEY
client_id       uuid              FK to cliente_vizu
horario_funcionamento json
prompt_base           varchar
enabled_tools         jsonb
```

**Status**: Fields already merged into `cliente_vizu` via migration `20251128_merge_configuracao_into_cliente_vizu.sql`

## Where Each Table Is Used

### `cliente_vizu` (105+ references)
- **Alembic migrations**: Initial schema, all FK relationships
- **SQLModel models**: All vizu_models classes (ClienteVizu, CredencialServicoExterno, etc.)
- **Service layer**: atendente_core, support_agent, vendas_agent, file_processing_worker
- **CRUD operations**: vizu_db_connector/crud.py (308+ lines)
- **Tests**: All test fixtures

### `clientes_vizu` (15+ references)
- **Supabase migrations**: RLS policies, OAuth user creation
- **analytics_api**: `ensure_cliente_vizu_exists()` - creates OAuth users
- **data_ingestion_api**: RLS context for file uploads, connector status
- **Frontend**: AuthContext, connector services
- **New tables**: `uploaded_files_metadata`, `connector_sync_history` (FK to clientes_vizu)

### `configuracao_negocio` (12 references - DEPRECATED)
- Still exists in schema but fields merged to `cliente_vizu`
- Migration `20251128_merge_configuracao_into_cliente_vizu.sql` copied data
- Should be dropped after verifying migration complete

## The Immediate Fix (Quick Solution)

**Change FK constraint on `credencial_servico_externo`** from `cliente_vizu` → `clientes_vizu`

**SQL Script**: [FIX_CREDENCIAL_FK_TO_CLIENTES_VIZU.sql](FIX_CREDENCIAL_FK_TO_CLIENTES_VIZU.sql)

This fixes the immediate error by allowing credentials to be saved for Google OAuth users.

## The Long-term Solution (Full Consolidation)

Eventually, you should consolidate to ONE table. Two options:

### Option A: Migrate Everything to `clientes_vizu` (RECOMMENDED)

**Advantages**:
- Already has `external_user_id` for OAuth/RLS
- Already has `created_at`/`updated_at` timestamps
- Used by newer services and Supabase RLS
- Better aligned with multi-tenant architecture

**Migration Steps**:
1. **Data Migration**: Copy all records from `cliente_vizu` → `clientes_vizu`
2. **FK Updates**: Update all FKs to point to `clientes_vizu`
3. **Code Updates**:
   - Update vizu_models to use `clientes_vizu` table name
   - Update all Alembic migrations (or create new migration)
   - Update 105+ code references
4. **Drop old tables**: `cliente_vizu`, `configuracao_negocio`

**Estimated Effort**: 3-4 hours (requires code changes across entire codebase)

### Option B: Dual-Write Pattern (Temporary Coexistence)

Keep both tables synchronized:
- New users → write to both tables
- OAuth users → `clientes_vizu` (with `external_user_id`)
- API key users → `cliente_vizu` (legacy)
- Sync data between tables via triggers

**Advantages**: Gradual migration, no breaking changes
**Disadvantages**: Complexity, data consistency risk, technical debt

## Why We Have This Problem

**Historical Context**:
1. **Original architecture**: Used `cliente_vizu` table with Alembic/SQLModel
2. **OAuth migration**: Created `clientes_vizu` table in Supabase for RLS with `external_user_id`
3. **Incomplete migration**: Some tables got updated (uploaded_files_metadata, connector_sync_history) but `credencial_servico_externo` still points to old table
4. **configuracao_negocio merge**: Fields merged to `cliente_vizu` but table still exists

## Recommendation

**For now**: Apply the quick fix (FK change) to unblock development

**Next sprint**: Plan full migration to `clientes_vizu` to eliminate technical debt

## Files to Apply

1. **[FIX_CREDENCIAL_FK_TO_CLIENTES_VIZU.sql](FIX_CREDENCIAL_FK_TO_CLIENTES_VIZU.sql)** - Run this NOW in Supabase Console
2. After FK fix is applied, test BigQuery connector creation
3. Verify credentials are saved successfully

---

**Issue**: FK constraint points to wrong table (cliente_vizu instead of clientes_vizu)
**Immediate Fix**: Change FK to clientes_vizu
**Long-term Fix**: Consolidate to single table (clientes_vizu)
**Status**: Ready to apply SQL fix ⚠️
