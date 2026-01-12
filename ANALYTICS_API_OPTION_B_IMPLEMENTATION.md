# Analytics API - Option B Implementation Complete

## ✅ What's Been Done

### 1. Table Consolidation (Migration Applied)
- **Migration**: [supabase/migrations/20260106_consolidate_data_ingestion_tables.sql](supabase/migrations/20260106_consolidate_data_ingestion_tables.sql)
- **Status**: ✅ Applied to Supabase

**Tables consolidated (9 → 6):**
- ✅ Enhanced `credencial_servico_externo` (added `connection_metadata`, `last_sync_at`)
- ✅ Enhanced `client_data_sources` (added `credential_id` FK, `source_columns`, mapping fields)
- ✅ Enhanced `connector_sync_history` (added `job_id`, `mapping_id`, `target_table`, etc.)
- ❌ Dropped `data_source_credentials` (merged into credencial_servico_externo)
- ❌ Dropped `data_source_mappings` (merged into client_data_sources)
- ❌ Dropped `ingestion_jobs` (merged into connector_sync_history)

---

### 2. Analytics API Updated - Query from Data Source Registry

**File**: [services/analytics_api/src/analytics_api/data_access/postgres_repository.py](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)

#### Changed: `get_silver_dataframe()` method

**Before (OLD - queried analytics_silver):**
```python
def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
    table_name = get_silver_table_name(client_id)  # Returns "analytics_silver"
    query = text(f"SELECT * FROM {table_name}")
    df = pd.read_sql(query, self.db_session.bind)
    return df
```

**After (NEW - queries from client_data_sources registry):**
```python
def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
    """
    NOVA ARQUITETURA (Option B):
    - Para BigQuery: query foreign table diretamente via FDW
    - Para CSV/VTEX: query raw_data_jsonb table
    - Mapeia colunas para o schema canônico esperado pelo MetricService
    """
    # 1. Look up data source location from registry
    data_source = self._get_data_source_location(client_id, 'bigquery', 'invoices')

    if not data_source:
        return pd.DataFrame()

    storage_type = data_source['storage_type']
    storage_location = data_source['storage_location']

    # 2. Query based on storage type
    if storage_type == 'foreign_table':
        # BigQuery foreign table - query directly
        query = text(f"SELECT * FROM {storage_location}")
        df = pd.read_sql(query, self.db_session.bind)

        # 3. Map BigQuery columns to canonical schema
        df = self._map_bigquery_columns(df)
        return df

    elif storage_type == 'jsonb_table':
        # CSV/VTEX data from raw_data_jsonb
        # ... parse JSONB and map columns
```

#### Added Helper Methods:

1. **`_get_data_source_location()`** - Queries `client_data_sources` registry
2. **`_map_bigquery_columns()`** - Maps BigQuery columns to canonical schema:
   ```python
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
   ```
3. **`_apply_column_mapping()`** - Applies custom column mapping from registry

---

### 3. ETL V2 Updated - Set credential_id FK

**File**: [services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py#L160-L179)

#### Changed: Data source registration (Line 160-179)

**Before:**
```python
await supabase_client.insert(
    "client_data_sources",
    {
        "client_id": client_id,
        "source_type": "bigquery",
        "resource_type": resource_type,
        "storage_type": "foreign_table",
        "storage_location": foreign_table_name,
        "column_mapping": None,
        "sync_status": "active",
    }
)
```

**After:**
```python
# Convert column list to JSONB format for source_columns
source_columns_jsonb = {col["name"]: col["type"] for col in foreign_table_columns}

await supabase_client.insert(
    "client_data_sources",
    {
        "client_id": client_id,
        "credential_id": int(credential_id),  # ← NEW: FK to credencial_servico_externo
        "source_type": "bigquery",
        "resource_type": resource_type,
        "storage_type": "foreign_table",
        "storage_location": foreign_table_name,
        "column_mapping": None,  # Analytics API uses default BigQuery mapping
        "source_columns": source_columns_jsonb,  # ← NEW: Store schema for reference
        "sync_status": "active",
    }
)
```

---

## 🔄 New Data Flow (Option B)

### BigQuery → Foreign Table → Analytics API → Gold Tables → Frontend

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Connects BigQuery (/dashboard/admin/fontes)            │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ETL V2 Service (data_ingestion_api)                         │
│    - Creates BigQuery foreign server (if not exists)           │
│    - Creates foreign table: bigquery.{client_id}_invoices      │
│    - Registers in client_data_sources:                         │
│      {                                                          │
│        client_id: "...",                                        │
│        credential_id: 123,  ← FK                                │
│        source_type: "bigquery",                                 │
│        resource_type: "invoices",                               │
│        storage_type: "foreign_table",                           │
│        storage_location: "bigquery.xxx_invoices",               │
│        source_columns: {"id_pedido": "text", ...}               │
│      }                                                          │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Analytics API (GET /dashboard/clientes)                     │
│    - Calls get_silver_dataframe(client_id)                     │
│    - Queries client_data_sources registry                      │
│    - Finds storage_location = "bigquery.xxx_invoices"          │
│    - Queries: SELECT * FROM bigquery.xxx_invoices              │
│    - Maps columns: id_pedido → order_id, etc.                  │
│    - Processes data with MetricService                         │
│    - Writes to analytics_gold_* tables                         │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Frontend Displays Data                                      │
│    - Reads from analytics_gold_customers                       │
│    - Reads from analytics_gold_orders                          │
│    - Reads from analytics_gold_products                        │
│    - Reads from analytics_gold_suppliers                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Next Steps

### 1. Rebuild Docker Containers

Both Analytics API and Data Ingestion API have been updated and need to be rebuilt:

```bash
# Rebuild both services
docker-compose build analytics_api data_ingestion_api

# Restart containers
docker-compose up -d analytics_api data_ingestion_api

# Check logs
docker-compose logs -f analytics_api data_ingestion_api
```

---

### 2. Test End-to-End Flow

#### Step 1: Trigger BigQuery Sync
1. Navigate to `/dashboard/admin/fontes`
2. Click "Conectar" on BigQuery connector
3. Fill in credentials:
   - Project ID
   - Dataset ID
   - Service Account JSON
4. Click "Conectar e Sincronizar"

**Expected Outcome:**
- Foreign table created: `bigquery.{client_id}_invoices`
- Registered in `client_data_sources` with `credential_id` FK
- No errors about analytics_silver

#### Step 2: Verify Data Source Registration

```sql
-- Check client_data_sources registry
SELECT
    id,
    client_id,
    credential_id,  -- Should be set!
    source_type,
    resource_type,
    storage_type,
    storage_location,
    source_columns,
    sync_status
FROM client_data_sources
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
  AND source_type = 'bigquery';

-- Check foreign table exists
SELECT * FROM bigquery_foreign_tables
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';

-- Query foreign table directly
SELECT * FROM bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices LIMIT 5;
```

#### Step 3: Test Analytics API

Call Analytics API endpoints to trigger data processing:

```bash
# Get dashboard stats (triggers MetricService)
curl -X GET "http://localhost:8005/dashboard/stats?periodo=30" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get clientes data (queries gold table)
curl -X GET "http://localhost:8005/dashboard/clientes?periodo=30" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected Flow:**
1. Analytics API receives request
2. Calls `get_silver_dataframe(client_id)`
3. Queries `client_data_sources` to find foreign table location
4. Queries foreign table: `SELECT * FROM bigquery.xxx_invoices`
5. Maps columns: `id_pedido` → `order_id`, etc.
6. MetricService processes data
7. Writes to `analytics_gold_customers`, `analytics_gold_orders`, etc.
8. Returns aggregated metrics

#### Step 4: Verify Gold Tables Populated

```sql
-- Check if gold tables have data
SELECT COUNT(*) FROM analytics_gold_customers WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
SELECT COUNT(*) FROM analytics_gold_orders WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
SELECT COUNT(*) FROM analytics_gold_products WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
SELECT COUNT(*) FROM analytics_gold_suppliers WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';

-- View sample data
SELECT * FROM analytics_gold_customers WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723' LIMIT 5;
```

#### Step 5: Check Frontend

Navigate to frontend pages and verify data displays:
- `/dashboard` - Should show metrics
- `/dashboard/clientes` - Should show customer data
- `/dashboard/produtos` - Should show product data
- `/dashboard/fornecedores` - Should show supplier data

---

## 🐛 Troubleshooting

### Issue: Analytics API returns empty data

**Check:**
1. Is `client_data_sources` populated?
   ```sql
   SELECT * FROM client_data_sources WHERE client_id = 'YOUR_CLIENT_ID';
   ```

2. Is `credential_id` set?
   ```sql
   SELECT credential_id FROM client_data_sources WHERE client_id = 'YOUR_CLIENT_ID';
   ```

3. Does foreign table exist?
   ```sql
   SELECT * FROM bigquery_foreign_tables WHERE client_id = 'YOUR_CLIENT_ID';
   ```

4. Can you query foreign table directly?
   ```sql
   SELECT * FROM bigquery.YOUR_CLIENT_ID_invoices LIMIT 5;
   ```

5. Check Analytics API logs:
   ```bash
   docker-compose logs analytics_api | grep -i "buscando dados\|querying\|mapeando"
   ```

### Issue: Column mapping errors

**Check Analytics API logs for:**
- "Nenhuma coluna BigQuery encontrada para mapear"
- "Colunas disponíveis: [...]"

**Fix:** Verify column names in foreign table match ETL V2 expectations:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'bigquery'
  AND table_name = 'YOUR_CLIENT_ID_invoices';
```

### Issue: FK violation on credential_id

**Check:**
```sql
-- Verify credential exists
SELECT id, client_id, nome_servico
FROM credencial_servico_externo
WHERE id = YOUR_CREDENTIAL_ID;

-- Check if client_data_sources has correct FK
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'client_data_sources'
  AND constraint_type = 'FOREIGN KEY';
```

---

## 📊 Performance Considerations

### BigQuery Query Costs

**Real-time queries via FDW will query BigQuery every time:**
- ✅ **Pros**: Always fresh data
- ⚠️ **Cons**: BigQuery charges per query ($5 per TB scanned)

**Mitigation:**
1. **Cache in gold tables** (current approach) - Analytics API writes to gold tables, frontend queries gold tables
2. **Use BigQuery BI Engine** - Google's free query cache (first 10GB/month free)
3. **Partition foreign tables** by date - Only query recent partitions

### Current Caching Strategy

The current implementation already caches data effectively:
- Foreign table → Analytics API processes → **Gold tables** (cached)
- Frontend queries gold tables (fast, no BigQuery cost)
- Only MetricService queries BigQuery via foreign table (infrequent)

---

## 📁 Files Modified

1. **[services/analytics_api/src/analytics_api/data_access/postgres_repository.py](services/analytics_api/src/analytics_api/data_access/postgres_repository.py)**
   - Updated `get_silver_dataframe()` to query from `client_data_sources` registry
   - Added `_get_data_source_location()` helper
   - Added `_map_bigquery_columns()` for column mapping
   - Added `_apply_column_mapping()` for custom mappings

2. **[services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py)**
   - Updated data source registration to set `credential_id` FK
   - Added `source_columns` JSONB to store schema

3. **[supabase/migrations/20260106_consolidate_data_ingestion_tables.sql](supabase/migrations/20260106_consolidate_data_ingestion_tables.sql)**
   - Enhanced 3 core tables (credencial_servico_externo, client_data_sources, connector_sync_history)
   - Migrated data from legacy tables
   - Dropped 3 legacy tables (data_source_credentials, data_source_mappings, ingestion_jobs)

---

## ✅ Summary

**Completed:**
- ✅ Table consolidation (9 → 6 tables)
- ✅ Analytics API updated to query from data source registry
- ✅ ETL V2 updated to set credential_id FK
- ✅ Column mapping implemented (BigQuery → canonical schema)
- ✅ Support for multiple storage types (foreign_table, jsonb_table)

**Ready to test:**
- ⏳ Rebuild Docker containers
- ⏳ Test BigQuery sync
- ⏳ Verify data flows to gold tables
- ⏳ Confirm frontend displays data

**Architecture achieved:**
```
BigQuery → Foreign Table (FDW) → Analytics API → Gold Tables → Frontend
```

No intermediate `analytics_silver` table for BigQuery data! ✅
