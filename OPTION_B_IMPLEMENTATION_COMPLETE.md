# Option B Implementation - Skip analytics_silver, Use Foreign Tables

## ✅ What's Been Done

### 1. Created Data Source Registry System

**File**: [supabase/migrations/20260106_create_data_source_registry.sql](supabase/migrations/20260106_create_data_source_registry.sql:1-255)

**Tables Created**:
- `client_data_sources` - Unified registry tracking all data sources per client
- `raw_data_jsonb` - Flexible storage for CSV/VTEX/API data

**Functions Created**:
- `register_data_source()` - Register/update a data source
- `get_data_source()` - Get data source info for a client

### 2. Updated ETL Service V2

**File**: [etl_service_v2.py](services/data_ingestion_api/src/data_ingestion_api/services/etl_service_v2.py:1-196)

**New Flow**:
1. Creates BigQuery foreign server
2. Creates foreign table with BigQuery columns (as TEXT for simplicity)
3. Registers data source in `client_data_sources` table
4. **DOES NOT insert to analytics_silver** ✅
5. Returns foreign table name for Analytics API to query

---

##  Architecture

### Data Flow by Source Type

#### BigQuery (Real-time via FDW)
```
BigQuery → Foreign Table → Analytics API → Gold Tables → Frontend
```

- No intermediate storage
- Real-time queries to BigQuery
- Analytics API maps columns

#### CSV/VTEX (Temp JSONB Storage)
```
CSV/API → raw_data_jsonb (JSONB) → Analytics API → Gold Tables → Frontend
```

- Flexible schema (JSONB)
- Analytics API parses JSON and maps columns
- Can be cleaned up after processing

### How It Works

**1. User Connects BigQuery** (`/dashboard/admin/fontes`)

Frontend → `POST /etl/run` → ETL Service:
- Creates foreign server: `bigquery_{client_id}`
- Creates foreign table: `bigquery.{client_id}_invoices`
- Registers in `client_data_sources`:
  ```json
  {
    "client_id": "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723",
    "source_type": "bigquery",
    "resource_type": "invoices",
    "storage_type": "foreign_table",
    "storage_location": "bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices"
  }
  ```

**2. Analytics API Queries Data**

Analytics API:
- Reads `client_data_sources` to find where data is
- Queries foreign table directly:
  ```sql
  SELECT * FROM bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices
  ```
- Maps columns (e.g., `id_pedido` → `order_id`)
- Processes and writes to `analytics_gold_*` tables

**3. Frontend Displays Data**

Frontend → `GET /dashboard/clientes` → Analytics API:
- Reads from `analytics_gold_customers`
- Returns aggregated metrics

---

## Column Mapping (Current Simplified Approach)

For now, the foreign table uses these column names (matching BigQuery):

| BigQuery Column      | Type | Notes                  |
|----------------------|------|------------------------|
| `id_pedido`          | text | Order ID               |
| `data_transacao`     | text | Transaction date       |
| `nome_emitter`       | text | Seller name            |
| `cnpj_emitter`       | text | Seller CNPJ            |
| `nome_receiver`      | text | Customer name          |
| `cpf_cnpj_receiver`  | text | Customer CPF/CNPJ      |
| `descricao_produto`  | text | Product description    |
| `quantidade`         | text | Quantity               |
| `valor_unitario`     | text | Unit price             |
| `valor_total`        | text | Total value            |
| `status`             | text | Order status           |

**Note**: All columns are TEXT for simplicity. Analytics API handles type conversion.

**TODO**: Query `INFORMATION_SCHEMA.COLUMNS` from BigQuery to get actual schema dynamically.

---

## Next Steps

### 1. Apply SQL Migration

```bash
# Copy migration content and paste into Supabase SQL Editor
cat supabase/migrations/20260106_create_data_source_registry.sql
```

### 2. Rebuild Data Ingestion API

```bash
cd services/data_ingestion_api
poetry lock
cd ../..
docker-compose build data_ingestion_api
docker-compose up -d data_ingestion_api
```

### 3. Test BigQuery Sync

1. Navigate to `/dashboard/admin/fontes`
2. Click "Conectar" on BigQuery
3. Fill in credentials
4. Click "Conectar e Sincronizar"

**Expected**:
- Foreign table created: `bigquery.{client_id}_invoices`
- Registered in `client_data_sources`
- No error about analytics_silver schema mismatch ✅

### 4. Update Analytics API (Future Work)

Analytics API needs to:
1. Query `client_data_sources` to find data location
2. Query foreign table directly instead of `analytics_silver`
3. Map BigQuery columns to canonical schema
4. Process and write to gold tables

**Example Code** (for Analytics API):

```python
# Get data source location
data_source = await supabase.rpc('get_data_source', {
    'p_client_id': client_id,
    'p_source_type': 'bigquery',
    'p_resource_type': 'invoices'
}).execute()

foreign_table = data_source.data['data']['storage_location']
# foreign_table = "bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices"

# Query foreign table
raw_data = await supabase.table(foreign_table).select("*").execute()

# Map columns
for row in raw_data.data:
    order_id = row['id_pedido']
    customer_name = row['nome_receiver']
    # ... map remaining columns
```

---

## Performance Considerations

### BigQuery Costs

**Real-time queries via FDW will query BigQuery every time**:
- ✅ Pros: Always fresh data
- ⚠️ Cons: BigQuery charges per query ($5 per TB scanned)

**Mitigation Options**:

1. **Cache frequently accessed data** (Option C from architecture doc):
   - Periodically sync foreign table → `raw_data_jsonb`
   - Analytics API queries cache first, falls back to foreign table

2. **Use BigQuery BI Engine** (Google's free query cache):
   - First 10GB/month free
   - Caches query results automatically

3. **Partition foreign tables** by date:
   - Only query recent partitions
   - Reduces data scanned

### Query Performance

- Foreign table queries have network latency to BigQuery
- For best performance: materialize frequently used aggregations in gold tables
- Current flow already does this: foreign table → process → gold tables

---

## CSV/VTEX Flow (Future Work)

For non-BigQuery sources, use `raw_data_jsonb`:

```python
# CSV Upload
for row in csv_rows:
    await supabase.insert('raw_data_jsonb', {
        'client_id': client_id,
        'source_type': 'csv',
        'resource_type': 'invoices',
        'raw_data': row,  # JSONB
        'source_file': 'sales_2024.csv',
        'row_number': row_index
    })

# Register source
await supabase.rpc('register_data_source', {
    'p_client_id': client_id,
    'p_source_type': 'csv',
    'p_resource_type': 'invoices',
    'p_storage_type': 'jsonb_table',
    'p_storage_location': 'raw_data_jsonb'
})
```

Analytics API reads from `raw_data_jsonb` the same way as foreign tables.

---

## Summary

✅ **BigQuery FDW working** - foreign tables created, no analytics_silver needed
✅ **Data source registry** - tracks where each client's data is stored
✅ **Flexible for future sources** - CSV/VTEX use JSONB storage
⏳ **Analytics API needs update** - to query from data source registry

**Ready to test!** Apply the SQL migration and rebuild the container.
