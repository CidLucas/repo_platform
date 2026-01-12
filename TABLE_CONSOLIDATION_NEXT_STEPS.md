# Table Consolidation - Implementation Summary & Next Steps

## ✅ What's Been Completed

### 1. Analysis Phase
- **Analyzed [table_details.sql](table_details.sql)** - Identified 9 data ingestion tables with 3 critical overlaps
- **Created [DATA_INGESTION_TABLE_CONSOLIDATION.md](DATA_INGESTION_TABLE_CONSOLIDATION.md)** - Detailed analysis of overlapping tables
- **Created migration SQL** - [supabase/migrations/20260106_consolidate_data_ingestion_tables.sql](supabase/migrations/20260106_consolidate_data_ingestion_tables.sql)

### 2. Key Findings

#### Tables to Consolidate (9 → 6)

**Before Consolidation (9 tables):**
1. `credencial_servico_externo` ✅ Keep (enhanced)
2. `data_source_credentials` ❌ Drop (merged into #1)
3. `client_data_sources` ✅ Keep (enhanced)
4. `data_source_mappings` ❌ Drop (merged into #3)
5. `connector_sync_history` ✅ Keep (enhanced)
6. `ingestion_jobs` ❌ Drop (merged into #5)
7. `raw_data_jsonb` ✅ Keep (no changes)
8. `integration_configs` ✅ Keep (OAuth - separate purpose)
9. `integration_tokens` ✅ Keep (OAuth - separate purpose)

**After Consolidation (6 tables):**
1. `credencial_servico_externo` - All service credentials
2. `client_data_sources` - Data source registry with FK to credentials
3. `connector_sync_history` - Job history with enhanced metrics
4. `raw_data_jsonb` - Flexible JSONB storage
5. `integration_configs` - OAuth configurations
6. `integration_tokens` - OAuth tokens

#### Critical Issues Fixed

1. **FK Type Mismatch** ✅
   - `connector_sync_history.credential_id` was `integer` (correct)
   - `ingestion_jobs.credential_id` was `uuid` (wrong - doesn't match any credential table!)
   - Fixed by consolidating into `connector_sync_history`

2. **Missing FK in `client_data_sources`** ✅
   - Migration adds `credential_id INTEGER REFERENCES credencial_servico_externo(id)`
   - Links data sources to their credentials

3. **Duplicate Credential Storage** ✅
   - Both `credencial_servico_externo` and `data_source_credentials` stored credentials
   - Consolidated into `credencial_servico_externo` (currently used by ETL V2)

---

## 🔄 Current Architecture Understanding

### Data Flow (Option B - Skip analytics_silver)

Based on [OPTION_B_IMPLEMENTATION_COMPLETE.md](OPTION_B_IMPLEMENTATION_COMPLETE.md):

```
BigQuery → Foreign Table → Analytics API → Gold Tables → Frontend
```

**Current State:**
- ✅ **ETL V2** creates foreign tables and registers in `client_data_sources` (see [etl_service_v2.py:163](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L163))
- ❌ **Analytics API** still expects to read from `analytics_silver` (see [postgres_repository.py:22](services/analytics_api/src/analytics_api/data_access/postgres_repository.py#L22))
- ❌ **Missing link:** Analytics API doesn't know about `client_data_sources` registry yet

**Problem:**
- ETL V2 creates foreign tables but doesn't write to `analytics_silver`
- Analytics API queries `analytics_silver` (which is empty)
- Data never flows to gold tables!

---

## 📋 Next Steps

### Step 1: Apply SQL Migration ⏳

**File:** [supabase/migrations/20260106_consolidate_data_ingestion_tables.sql](supabase/migrations/20260106_consolidate_data_ingestion_tables.sql)

**What it does:**
1. Adds columns to `credencial_servico_externo`: `connection_metadata`, `last_sync_at`
2. Adds columns to `client_data_sources`: `credential_id` FK, `source_columns`, `unmapped_columns`, `match_confidence`, review fields
3. Adds columns to `connector_sync_history`: `job_id`, `mapping_id`, `target_table`, `progress_percent`, `error_details`
4. Migrates data from legacy tables (if any exists)
5. Drops legacy tables: `data_source_credentials`, `data_source_mappings`, `ingestion_jobs`

**How to apply:**
```bash
# Copy migration content
cat supabase/migrations/20260106_consolidate_data_ingestion_tables.sql

# Paste into Supabase SQL Editor and run
# Or apply via Supabase CLI
supabase db push
```

---

### Step 2: Update ETL V2 to Set credential_id ⏳

**File:** [services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py)

**Current code (Line 163-174):**
```python
await supabase_client.insert(
    "client_data_sources",
    {
        "client_id": client_id,
        "source_type": "bigquery",
        "resource_type": resource_type,
        "storage_type": "foreign_table",
        "storage_location": foreign_table_name,
        "column_mapping": None,  # Analytics API will handle mapping
        "sync_status": "active",
    }
)
```

**Updated code (add credential_id):**
```python
await supabase_client.insert(
    "client_data_sources",
    {
        "client_id": client_id,
        "credential_id": credential_id,  # ← ADD THIS
        "source_type": "bigquery",
        "resource_type": resource_type,
        "storage_type": "foreign_table",
        "storage_location": foreign_table_name,
        "column_mapping": None,
        "source_columns": foreign_table_columns,  # ← ADD THIS
        "sync_status": "active",
    }
)
```

---

### Step 3: Update Analytics API to Query Foreign Tables ⏳

**Current Flow:**
```python
# services/analytics_api/src/analytics_api/data_access/postgres_repository.py:22
def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
    table_name = get_silver_table_name(client_id)  # Returns "analytics_silver"
    query = text(f"SELECT * FROM {table_name}")
    df = pd.read_sql(query, self.db_session.bind)
    return df
```

**New Flow (Option B):**
```python
def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
    """
    NEW: Query from client_data_sources registry to find where data is stored.
    For BigQuery: query foreign table directly
    For CSV/VTEX: query raw_data_jsonb
    """
    # 1. Look up data source location
    data_source = self._get_data_source_location(client_id, 'bigquery', 'invoices')

    if not data_source:
        logger.warning(f"No data source found for client {client_id}")
        return pd.DataFrame()

    storage_type = data_source['storage_type']
    storage_location = data_source['storage_location']
    column_mapping = data_source.get('column_mapping')

    # 2. Query based on storage type
    if storage_type == 'foreign_table':
        # BigQuery foreign table
        query = text(f"SELECT * FROM {storage_location}")
        df = pd.read_sql(query, self.db_session.bind)

        # 3. Map columns to canonical schema
        if column_mapping:
            df = self._apply_column_mapping(df, column_mapping)
        else:
            # Use default BigQuery column names
            df = self._map_bigquery_columns(df)

        return df

    elif storage_type == 'jsonb_table':
        # CSV/VTEX data from raw_data_jsonb
        query = text("""
            SELECT raw_data
            FROM raw_data_jsonb
            WHERE client_id = :client_id
              AND source_type = :source_type
              AND resource_type = :resource_type
        """)
        result = self.db_session.execute(query, {
            'client_id': client_id,
            'source_type': data_source['source_type'],
            'resource_type': data_source['resource_type']
        })

        # Parse JSONB rows into DataFrame
        rows = [row['raw_data'] for row in result]
        df = pd.DataFrame(rows)

        # Map columns
        if column_mapping:
            df = self._apply_column_mapping(df, column_mapping)

        return df

    else:
        logger.error(f"Unknown storage type: {storage_type}")
        return pd.DataFrame()


def _get_data_source_location(self, client_id: str, source_type: str, resource_type: str) -> dict:
    """Query client_data_sources registry"""
    query = text("""
        SELECT storage_type, storage_location, column_mapping, source_columns
        FROM client_data_sources
        WHERE client_id = :client_id
          AND source_type = :source_type
          AND resource_type = :resource_type
          AND sync_status = 'active'
        LIMIT 1
    """)
    result = self.db_session.execute(query, {
        'client_id': client_id,
        'source_type': source_type,
        'resource_type': resource_type
    }).fetchone()

    if not result:
        return None

    return {
        'storage_type': result.storage_type,
        'storage_location': result.storage_location,
        'column_mapping': result.column_mapping,
        'source_columns': result.source_columns,
        'source_type': source_type,
        'resource_type': resource_type
    }


def _map_bigquery_columns(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Map BigQuery column names to canonical schema.

    BigQuery columns (from etl_service_v2.py:126-138):
        id_pedido, data_transacao, nome_emitter, cnpj_emitter,
        nome_receiver, cpf_cnpj_receiver, descricao_produto,
        quantidade, valor_unitario, valor_total, status

    Canonical schema (analytics_silver expected columns):
        order_id, data_transacao, emitter_nome, emitter_cnpj,
        receiver_nome, receiver_cpf_cnpj, raw_product_description,
        quantidade, valor_unitario, valor_total_emitter, status
    """
    column_map = {
        'id_pedido': 'order_id',
        'data_transacao': 'data_transacao',
        'nome_emitter': 'emitter_nome',
        'cnpj_emitter': 'emitter_cnpj',
        'nome_receiver': 'receiver_nome',
        'cpf_cnpj_receiver': 'receiver_cpf_cnpj',
        'descricao_produto': 'raw_product_description',
        'quantidade': 'quantidade',
        'valor_unitario': 'valor_unitario',
        'valor_total': 'valor_total_emitter',
        'status': 'status'
    }

    return df.rename(columns=column_map)


def _apply_column_mapping(self, df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """Apply custom column mapping from client_data_sources"""
    if not column_mapping:
        return df

    return df.rename(columns=column_mapping)
```

---

### Step 4: Test End-to-End Flow ⏳

**Test Sequence:**

1. **Verify Migration Applied**
   ```sql
   -- Check new columns exist
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'client_data_sources'
     AND column_name IN ('credential_id', 'source_columns', 'unmapped_columns');

   -- Check legacy tables dropped
   SELECT table_name
   FROM information_schema.tables
   WHERE table_schema = 'public'
     AND table_name IN ('data_source_credentials', 'data_source_mappings', 'ingestion_jobs');
   ```

2. **Trigger BigQuery Sync**
   - Navigate to `/dashboard/admin/fontes`
   - Click "Conectar" on BigQuery connector
   - Fill credentials and click "Conectar e Sincronizar"

3. **Verify Foreign Table Created**
   ```sql
   -- Check client_data_sources registry
   SELECT *
   FROM client_data_sources
   WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
     AND source_type = 'bigquery';

   -- Check foreign table exists
   SELECT foreign_table_name
   FROM bigquery_foreign_tables
   WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';

   -- Query foreign table directly
   SELECT * FROM bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices LIMIT 5;
   ```

4. **Test Analytics API**
   - Call `GET /dashboard/clientes` endpoint
   - Should query foreign table → process → write to `analytics_gold_customers`
   - Verify data appears in frontend

5. **Check Gold Tables**
   ```sql
   SELECT COUNT(*) FROM analytics_gold_customers WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
   SELECT COUNT(*) FROM analytics_gold_orders WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
   SELECT COUNT(*) FROM analytics_gold_products WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
   SELECT COUNT(*) FROM analytics_gold_suppliers WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
   ```

---

## 🎯 Summary

**What we've done:**
- ✅ Analyzed and identified 3 overlapping table groups
- ✅ Created consolidation plan (9 → 6 tables)
- ✅ Created SQL migration to enhance and consolidate tables
- ✅ Reviewed Analytics API architecture

**What needs to be done:**
1. Apply SQL migration to Supabase
2. Update ETL V2 to set `credential_id` in `client_data_sources`
3. Update Analytics API to query from `client_data_sources` registry and foreign tables
4. Test end-to-end BigQuery → Foreign Table → Analytics API → Gold Tables flow

**Key Decision:**
- Following **Option B** architecture: BigQuery data stays in foreign tables, Analytics API queries directly
- No intermediate `analytics_silver` table for BigQuery (only for CSV/VTEX via `raw_data_jsonb`)

---

## 📁 Files Created

1. [DATA_INGESTION_TABLE_CONSOLIDATION.md](DATA_INGESTION_TABLE_CONSOLIDATION.md) - Detailed analysis
2. [supabase/migrations/20260106_consolidate_data_ingestion_tables.sql](supabase/migrations/20260106_consolidate_data_ingestion_tables.sql) - Migration SQL
3. [TABLE_CONSOLIDATION_NEXT_STEPS.md](TABLE_CONSOLIDATION_NEXT_STEPS.md) - This file

Ready to proceed with the migration! 🚀
