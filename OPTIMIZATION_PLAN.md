# Data Ingestion & Observability Optimization Plan

**Date:** 2026-01-09
**Status:** Planning Phase

---

## Issues Identified

### 1. Observability/OTLP Collector Issues
**Symptoms:**
```
ERROR: Failed to export traces to otel-collector:4317, StatusCode.UNAVAILABLE
WARNING: Transient error StatusCode.UNAVAILABLE encountered while exporting traces
```

**Root Cause:**
- OTLP collector service not configured/running in docker-compose
- Application tries to export telemetry but collector is unavailable
- Non-blocking but generates noise in logs

**Impact:** Low priority - monitoring only, doesn't affect functionality

---

### 2. Inefficient Data Ingestion (HIGH PRIORITY)

#### Problem 2A: Full Table Scans
**Current Behavior:**
```python
# BigQuery FDW pulls ENTIRE table every time
CREATE FOREIGN TABLE bigquery.client_invoices (...)
  OPTIONS (table 'project.dataset.invoices')

# No filtering at source
SELECT * FROM bigquery.client_invoices  -- Pulls ALL columns, ALL rows
```

**Issues:**
1. **Bandwidth waste:** Transferring unnecessary columns
2. **BigQuery cost:** Full table scans are expensive
3. **Latency:** Large data transfers slow down sync
4. **Memory:** Loading full datasets into memory

#### Problem 2B: No Incremental Loading
**Current Behavior:**
- Every ETL run queries ALL records from BigQuery
- No timestamp tracking (last_synced_at)
- No watermark/checkpoint mechanism
- Redundant data transfer for unchanged records

**Example:**
```
Sync 1: Transfer 100k records (2023-01-01 to 2024-01-01)
Sync 2: Transfer 100k records AGAIN + 1k new records (2024-01-02)
  ❌ Should only transfer 1k new records!
```

---

## Optimization Strategy

### Phase 1: Observability Cleanup (Quick Win)
**Goal:** Eliminate noisy logs, optional telemetry storage

**Tasks:**
1. ✅ Make OTLP exporter optional via environment variable
2. ✅ Add graceful fallback when collector unavailable
3. ✅ Create observability summary table in database
4. ✅ Store periodic health/trace summaries

**Database Schema:**
```sql
CREATE TABLE observability_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_name TEXT NOT NULL,
  report_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  report_period_start TIMESTAMPTZ NOT NULL,
  report_period_end TIMESTAMPTZ NOT NULL,

  -- Metrics
  total_requests INTEGER,
  failed_requests INTEGER,
  avg_response_time_ms NUMERIC,
  p95_response_time_ms NUMERIC,
  p99_response_time_ms NUMERIC,

  -- Errors
  error_count INTEGER,
  top_errors JSONB,  -- Array of {error_type, count, last_seen}

  -- Traces (if available)
  trace_export_success BOOLEAN,
  trace_export_failures INTEGER,

  -- Metadata
  metadata JSONB,

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_observability_service_time
  ON observability_reports(service_name, report_timestamp DESC);
```

---

### Phase 2: Column-Level Filtering (Medium Priority)

**Goal:** Only fetch columns we actually need from BigQuery

**Approach:**

#### 2.1: Schema Registry Enhancement
```python
# Add "required_columns" to schema definitions
CANONICAL_SCHEMAS = {
    "orders": {
        "required_columns": [
            "order_id",          # Always needed
            "customer_id",       # Always needed
            "order_date",        # Always needed
            "total_amount",      # For revenue calculations
            "status"             # For status tracking
        ],
        "optional_columns": [
            "shipping_address",  # Nice to have but not critical
            "notes"              # Usually not analyzed
        ]
    }
}
```

#### 2.2: Smart Foreign Table Creation
```python
async def create_foreign_table_optimized(
    self,
    client_id: str,
    table_name: str,
    bigquery_table: str,
    all_columns: List[dict],  # From BigQuery schema discovery
    schema_type: str  # "orders", "invoices", etc.
) -> dict:
    """
    Create foreign table with only REQUIRED columns from schema registry.
    """
    # Get required columns for this schema type
    required_cols = schema_registry.get_required_columns(schema_type)

    # Filter to only required columns
    filtered_columns = [
        col for col in all_columns
        if col['name'] in required_cols
    ]

    logger.info(
        f"Optimized: {len(all_columns)} -> {len(filtered_columns)} columns "
        f"for {schema_type}"
    )

    # Create foreign table with filtered columns
    return await self.create_foreign_table(
        client_id=client_id,
        table_name=table_name,
        bigquery_table=bigquery_table,
        columns=filtered_columns  # ✅ Only required columns
    )
```

#### 2.3: BigQuery Query Optimization
```sql
-- Instead of:
SELECT * FROM `project.dataset.orders`  -- ❌ All 50 columns

-- Generate:
SELECT
  order_id,
  customer_id,
  order_date,
  total_amount,
  status
FROM `project.dataset.orders`  -- ✅ Only 5 columns
```

**Expected Impact:**
- 📉 50-80% reduction in data transfer volume
- 📉 30-50% reduction in BigQuery scan costs
- 📉 40-60% reduction in sync latency

---

### Phase 3: Incremental Loading (HIGH PRIORITY)

**Goal:** Only sync NEW/CHANGED records since last successful sync

**Implementation:**

#### 3.1: Sync Watermark Table
```sql
CREATE TABLE sync_watermarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clientes_vizu(id),
  table_name TEXT NOT NULL,
  schema_type TEXT NOT NULL,  -- 'orders', 'invoices', etc.

  -- Watermark tracking
  last_synced_at TIMESTAMPTZ NOT NULL,
  last_synced_value TIMESTAMPTZ,  -- Max timestamp from last sync

  -- Sync metadata
  last_sync_status TEXT,  -- 'success', 'partial', 'failed'
  records_synced INTEGER,
  sync_duration_ms INTEGER,

  -- Foreign table reference
  foreign_table_name TEXT,
  bigquery_table TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(client_id, table_name)
);
```

#### 3.2: Timestamp Column Detection
```python
def detect_timestamp_column(columns: List[dict]) -> str | None:
    """
    Auto-detect primary timestamp column for incremental loading.

    Priority order:
    1. updated_at / modified_at
    2. created_at / inserted_at
    3. order_date / transaction_date / invoice_date
    4. Any TIMESTAMPTZ column
    """
    priority_names = [
        ['updated_at', 'modified_at', 'last_modified'],
        ['created_at', 'inserted_at', 'created'],
        ['order_date', 'transaction_date', 'invoice_date', 'date'],
    ]

    for priority_group in priority_names:
        for col in columns:
            if col['name'].lower() in priority_group:
                if col['type'] in ['timestamptz', 'timestamp', 'date']:
                    return col['name']

    # Fallback: any timestamp column
    for col in columns:
        if col['type'] in ['timestamptz', 'timestamp']:
            return col['name']

    return None
```

#### 3.3: Incremental Sync Logic
```python
async def sync_incremental(
    self,
    client_id: str,
    table_name: str,
    schema_type: str
) -> dict:
    """
    Perform incremental sync using watermark.
    """
    # Get last watermark
    watermark = await self._get_sync_watermark(client_id, table_name)

    if not watermark or not watermark.get('timestamp_column'):
        logger.warning(f"No watermark found for {table_name}, performing full sync")
        return await self.sync_full(client_id, table_name, schema_type)

    last_value = watermark['last_synced_value']
    ts_column = watermark['timestamp_column']

    # Build incremental WHERE clause
    where_clause = f"{ts_column} > '{last_value}'"

    logger.info(
        f"Incremental sync for {table_name}: "
        f"fetching records where {where_clause}"
    )

    # Sync only new records
    result = await self.extract_data_to_supabase(
        foreign_table=watermark['foreign_table_name'],
        destination_table=f"analytics_raw_{schema_type}",
        where_clause=where_clause  # ✅ Only new records
    )

    if result['success']:
        # Update watermark with max timestamp from this batch
        new_max = await self._get_max_timestamp(
            table=watermark['foreign_table_name'],
            column=ts_column
        )

        await self._update_watermark(
            client_id=client_id,
            table_name=table_name,
            last_value=new_max,
            records_synced=result['rows_inserted']
        )

    return result
```

#### 3.4: Smart Full vs Incremental Decision
```python
async def sync_auto(
    self,
    client_id: str,
    table_name: str,
    schema_type: str,
    force_full: bool = False
) -> dict:
    """
    Automatically decide between full and incremental sync.
    """
    if force_full:
        return await self.sync_full(client_id, table_name, schema_type)

    watermark = await self._get_sync_watermark(client_id, table_name)

    # Conditions for full sync:
    if not watermark:
        logger.info("No watermark exists, performing initial full sync")
        return await self.sync_full(client_id, table_name, schema_type)

    if watermark.get('last_sync_status') == 'failed':
        logger.warning("Last sync failed, performing full sync")
        return await self.sync_full(client_id, table_name, schema_type)

    # Check if watermark is too old (>7 days)
    if self._is_watermark_stale(watermark['last_synced_at'], max_age_days=7):
        logger.info("Watermark is stale (>7 days), performing full sync")
        return await self.sync_full(client_id, table_name, schema_type)

    # Otherwise, incremental
    return await self.sync_incremental(client_id, table_name, schema_type)
```

**Expected Impact:**
- 📉 90-99% reduction in data transfer for mature datasets
- 📉 80-95% reduction in BigQuery scan costs
- 📉 70-90% reduction in sync latency
- 📈 10-100x faster sync operations

---

### Phase 4: Query Optimization

**Goal:** Optimize BigQuery foreign table queries

#### 4.1: Partition Pruning
```python
# If BigQuery table is partitioned by date
async def create_foreign_table_with_partition_filter(
    self,
    bigquery_table: str,
    partition_column: str = "_PARTITIONDATE"
) -> dict:
    """
    Add partition filter to reduce BigQuery scan costs.
    """
    # Only scan last 90 days of partitions
    partition_filter = f"""
    WHERE {partition_column} >= CURRENT_DATE() - 90
    """

    # BigQuery FDW can push down this filter
    return await self.create_foreign_table(
        bigquery_table=bigquery_table,
        where_clause=partition_filter  # ✅ Partition pruning
    )
```

#### 4.2: Batch Processing
```python
async def sync_in_batches(
    self,
    foreign_table: str,
    batch_size: int = 10000
) -> dict:
    """
    Process large tables in batches to avoid memory issues.
    """
    total_synced = 0
    offset = 0

    while True:
        result = await self.extract_data_to_supabase(
            foreign_table=foreign_table,
            destination_table="analytics_raw",
            limit=batch_size,
            offset=offset
        )

        rows = result.get('rows_inserted', 0)
        if rows == 0:
            break

        total_synced += rows
        offset += batch_size

        logger.info(f"Batch complete: {total_synced} total rows synced")

    return {'success': True, 'total_rows': total_synced}
```

---

## Implementation Priority

### 🔴 Phase 1 - Immediate (Week 1)
1. Make OTLP exporter optional
2. Add graceful fallback for missing collector
3. Suppress noisy observability logs

### 🟡 Phase 2 - Short Term (Week 2)
1. Create observability_reports table
2. Implement summary report storage
3. Add column filtering to schema registry
4. Update foreign table creation to use filtered columns

### 🟢 Phase 3 - Medium Term (Week 3-4)
1. Create sync_watermarks table
2. Implement timestamp column detection
3. Build incremental sync logic
4. Add auto full vs incremental decision

### 🔵 Phase 4 - Long Term (Month 2)
1. Add partition pruning support
2. Implement batch processing
3. Add sync monitoring dashboard
4. Optimize BigQuery query patterns

---

## Success Metrics

### Performance
- **Sync Time:** Target 80% reduction for incremental syncs
- **Data Transfer:** Target 70% reduction in bandwidth
- **BigQuery Costs:** Target 60% reduction in scan costs

### Reliability
- **Sync Success Rate:** Target >99% success rate
- **Error Recovery:** Automatic retry with exponential backoff
- **Data Consistency:** Zero data loss, at-least-once delivery

### Monitoring
- **Observability Reports:** 95% of reports successfully stored
- **Watermark Accuracy:** <1 minute lag in watermark updates
- **Alert Response:** <5 minute detection of sync failures

---

## Risks & Mitigations

### Risk 1: Timestamp Column Not Available
**Mitigation:**
- Fallback to full sync
- Warn user in connector setup
- Document best practices for timestamp columns

### Risk 2: Data Gaps During Incremental Sync
**Mitigation:**
- Periodic full sync validation (weekly)
- Watermark staleness detection
- Manual full sync trigger option

### Risk 3: BigQuery Schema Changes
**Mitigation:**
- Schema version tracking
- Automatic re-discovery on sync failure
- Graceful degradation to full sync

---

## Next Steps

1. **Review this plan** with team
2. **Prioritize phases** based on business impact
3. **Create implementation tickets** for Phase 1
4. **Set up monitoring** for baseline metrics
5. **Start Phase 1 implementation**

---

## Questions for Discussion

1. Should we implement column filtering before or after incremental loading?
2. What's the acceptable sync latency for incremental loads? (target: <30s)
3. Should we store raw observability events or only summaries?
4. Do we need real-time alerts for sync failures?
5. Should watermarks be per-table or per-connector?
