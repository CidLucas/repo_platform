# BigQuery FDW - Revised Architecture

## Current Issue

The ETL service is trying to insert BigQuery data into `analytics_silver`, but:

1. **BigQuery tables can have ANY schema** (different column names, types, etc.)
2. **analytics_silver has a FIXED schema** (order_id, emitter_nome, etc.)
3. **This causes type mismatch errors** like: `column "id" is of type uuid but expression is of type jsonb`

## Current Flow (BROKEN)

```
BigQuery → Foreign Table → analytics_silver (FIXED SCHEMA ❌) → Gold Tables → Frontend
```

**Problem**: Can't insert arbitrary BigQuery columns into fixed `analytics_silver` schema

---

## Solution Options

### Option A: Make analytics_silver Flexible (JSONB)

**Change**: Modify `analytics_silver` to use JSONB for flexible data storage

```sql
CREATE TABLE analytics_silver (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT NOT NULL,
  source_type TEXT NOT NULL,  -- 'bigquery', 'csv', etc.
  resource_type TEXT,  -- 'invoices', 'products', etc.
  raw_data JSONB NOT NULL,  -- Stores entire row from BigQuery
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Pros**:
- Flexible - works with ANY BigQuery schema
- Simple ETL: just dump BigQuery rows as JSON

**Cons**:
- Analytics API needs to parse JSONB
- Harder to query structured data

---

### Option B: Skip analytics_silver Entirely (RECOMMENDED)

**Change**: Have Analytics API query BigQuery foreign tables directly

```
BigQuery → Foreign Table (permanent) → Analytics API queries directly → Gold Tables → Frontend
```

**How it works**:

1. **Data Ingestion API** creates foreign tables (one-time setup):
   ```sql
   -- Creates: bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices
   SELECT create_bigquery_foreign_table(...);
   ```

2. **Analytics API** queries foreign table directly:
   ```python
   # Instead of: SELECT * FROM analytics_silver
   # Use: SELECT * FROM bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices

   foreign_table = f"bigquery.{client_id.replace('-', '_')}_invoices"
   data = await supabase.table(foreign_table).select("*").execute()
   ```

3. **Analytics API** processes and writes to gold tables (as before)

**Pros**:
- No intermediate `analytics_silver` table needed
- Real-time data from BigQuery (via FDW)
- Simple architecture

**Cons**:
- Slower queries (hits BigQuery every time)
- No caching of BigQuery data

---

### Option C: Hybrid - Cache BigQuery Data as JSONB

**Combine Options A + B**: Use foreign tables for real-time queries, cache in `analytics_silver` for performance

```
BigQuery → Foreign Table (real-time) ─┐
                                       ├→ Analytics API → Gold Tables → Frontend
analytics_silver (cached JSONB) ──────┘
```

1. **Real-time mode**: Query foreign table directly
2. **Cached mode**: Sync foreign table → `analytics_silver` (JSONB) for faster queries
3. **Analytics API** can choose which source to use

---

## Recommendation: Option B (Skip analytics_silver)

**Why?**
- Simplest architecture
- Works with Supabase FDW design
- No schema mapping needed
- Analytics API already processes raw data

**Changes Needed**:

### 1. Update ETL Service (Don't insert to analytics_silver)

```python
# OLD (BROKEN):
await bigquery_wrapper_service.extract_data_to_supabase(
    foreign_table=foreign_table_name,
    destination_table="analytics_silver",  # ❌ REMOVE THIS
    ...
)

# NEW:
# Just create the foreign table - that's it!
# Analytics API will query it directly
foreign_table_result = await bigquery_wrapper_service.create_foreign_table(
    client_id=client_id,
    table_name=resource_type,
    bigquery_table=bigquery_table,
    columns=bigquery_columns,  # Get from BigQuery schema
    location="US"
)

return {
    "status": "success",
    "foreign_table": foreign_table_result.get('foreign_table_name'),
    "message": f"Foreign table created: {foreign_table_result.get('foreign_table_name')}"
}
```

### 2. Update Analytics API (Query foreign table)

```python
# OLD:
silver_table = "analytics_silver"
data = await supabase.table(silver_table).select("*").execute()

# NEW:
foreign_table = f"bigquery.{client_id.replace('-', '_')}_{resource_type}"
data = await supabase.table(foreign_table).select("*").execute()
```

### 3. Store Foreign Table Mapping

Add a table to track which foreign tables exist for each client:

```sql
CREATE TABLE client_data_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT NOT NULL,
  source_type TEXT NOT NULL,  -- 'bigquery', 'csv', 'api'
  resource_type TEXT NOT NULL,  -- 'invoices', 'products'
  foreign_table_name TEXT,  -- 'bigquery.client_invoices'
  table_schema JSONB,  -- Column definitions
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(client_id, source_type, resource_type)
);
```

---

## Implementation Steps

1. **Update ETL Service**: Remove `extract_data_to_supabase` call
2. **Get BigQuery Schema**: Query `INFORMATION_SCHEMA.COLUMNS` to get actual columns
3. **Create Foreign Table**: With correct BigQuery column types
4. **Update Analytics API**: Query foreign table instead of `analytics_silver`
5. **Test**: Verify data flows through correctly

---

## Questions for User

1. **Do you want real-time BigQuery queries** (Option B) **or cached data** (Option C)?
2. **Should we keep analytics_silver** for other data sources (CSV uploads)?
3. **Which BigQuery columns map to analytics fields** (order_id, customer_name, etc.)?

Let me know which option you prefer and I'll implement it!
