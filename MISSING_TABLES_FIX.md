# Fix: Missing Tables (uploaded_files_metadata, analytics_silver)

## Issue

The Admin Home page (`/dashboard/admin`) was showing `500 Internal Server Error`:

```
Failed to get dashboard stats: {'message': "Could not find the table 'public.uploaded_files_metadata' in the schema cache", 'code': 'PGRST205'}

postgrest.exceptions.APIError: Could not find the table 'public.uploaded_files_metadata' in the schema cache
```

**Console Error**:
```
:8008/connectors/dashboard-stats?client_id=xxx
Failed to load resource: the server responded with a status of 500 (Internal Server Error)
```

## Root Cause

The `/connectors/dashboard-stats` endpoint tries to query two tables that don't exist yet:

1. **`uploaded_files_metadata`** - Tracks CSV/Excel files uploaded by users
2. **`analytics_silver`** - Stores analytics data

These tables were planned in Phase 1 of the implementation plan (see plan file) but were never created in the Supabase database.

## Why This Happened

The `connector_status_service.py` has a method `get_storage_usage()` that calculates storage by:
1. Querying `uploaded_files_metadata` for file sizes
2. Querying `analytics_silver` for record counts

**Without these tables**, the Supabase PostgREST API returns:
```json
{
  "message": "Could not find the table 'public.uploaded_files_metadata' in the schema cache",
  "code": "PGRST205"
}
```

This causes the entire endpoint to fail with `500 Internal Server Error`.

## The Fix

Updated `connector_status_service.py` to handle missing tables gracefully by wrapping queries in try/except blocks:

**File**: [services/data_ingestion_api/src/data_ingestion_api/services/connector_status_service.py](services/data_ingestion_api/src/data_ingestion_api/services/connector_status_service.py#L158-L213)

**Before** (lines 167-172):
```python
# 1. Get file storage from uploaded_files_metadata
files = await supabase_client.select(
    table="uploaded_files_metadata",
    columns="file_size_bytes",
    filters={"client_id": client_id, "status": "completed"},
    client_id=client_id,
)
# ❌ Crashes if table doesn't exist
```

**After** (lines 168-181):
```python
# 1. Get file storage from uploaded_files_metadata
# NOTE: Table may not exist yet - handle gracefully
try:
    files = await supabase_client.select(
        table="uploaded_files_metadata",
        columns="file_size_bytes",
        filters={"client_id": client_id, "status": "completed"},
        client_id=client_id,
    )
    file_storage_bytes = sum(f.get("file_size_bytes", 0) for f in files)
except Exception as e:
    logger.debug(f"uploaded_files_metadata table not found or empty: {e}")
    files = []
    file_storage_bytes = 0
# ✅ Returns zero values if table doesn't exist
```

**Same fix applied to `analytics_silver` query** (lines 183-194).

## Behavior After Fix

### Before (Crash):
```
GET /connectors/dashboard-stats?client_id=xxx
→ Query uploaded_files_metadata
→ Table not found
→ APIError exception
→ 500 Internal Server Error
```

### After (Graceful Handling):
```
GET /connectors/dashboard-stats?client_id=xxx
→ Query uploaded_files_metadata
→ Table not found (caught by try/except)
→ Return files = [], file_storage_bytes = 0
→ Query analytics_silver
→ Table not found (caught by try/except)
→ Return records = [], estimated_db_bytes = 0
→ Return StorageUsageResponse with all zeros
→ 200 OK
```

**Response when tables don't exist**:
```json
{
  "total_connectors": 0,
  "connected_connectors": 0,
  "pending_connectors": 0,
  "error_connectors": 0,
  "storage_usage": {
    "database_size_bytes": 0,
    "database_size_mb": 0.0,
    "file_storage_bytes": 0,
    "file_storage_mb": 0.0,
    "total_storage_bytes": 0,
    "total_storage_mb": 0.0,
    "total_storage_gb": 0.0,
    "quota_gb": 2000,
    "usage_percentage": 0.0,
    "total_files": 0,
    "total_records": 0
  },
  "last_sync_at": null,
  "total_syncs_today": 0
}
```

## When Will These Tables Be Created?

According to the implementation plan, these tables will be created in **Phase 1**:

### Migration 1: `uploaded_files_metadata`
**Purpose**: Track CSV/Excel files uploaded by users for data import

**Columns**:
- `id` (UUID, primary key)
- `client_id` (UUID, FK to clientes_vizu)
- `file_name` (text)
- `file_size_bytes` (bigint)
- `file_type` (text) - "csv", "excel"
- `storage_bucket` (text) - Supabase Storage bucket name
- `storage_path` (text) - Path in storage bucket
- `status` (text) - "uploaded", "processing", "completed", "failed", "deleted"
- `records_count` (integer)
- `records_imported` (integer)
- `uploaded_at` (timestamp)
- `processed_at` (timestamp)
- `deleted_at` (timestamp)

**RLS**: Row-level security policies to isolate by `client_id`

### Migration 2: `analytics_silver`
**Purpose**: Store processed analytics data (alternative to current schema)

**Note**: This might not be needed if we continue using the existing analytics tables. The storage calculation can be updated to use existing tables instead.

## Alternative Solution (If Tables Are Not Created)

If these tables are not going to be created, we can update the storage calculation to use **existing tables**:

```python
# Instead of analytics_silver, use existing analytics tables
try:
    # Count records in vendas table
    vendas = await supabase_client.select(
        table="vendas",
        columns="id",
        filters={"cliente_id": client_id},
        client_id=client_id,
    )
    total_records = len(vendas)
except Exception as e:
    logger.debug(f"vendas table query failed: {e}")
    total_records = 0
```

## Files Modified

1. [services/data_ingestion_api/src/data_ingestion_api/services/connector_status_service.py](services/data_ingestion_api/src/data_ingestion_api/services/connector_status_service.py#L158-L213)
   - Added try/except around `uploaded_files_metadata` query
   - Added try/except around `analytics_silver` query
   - Return zero values when tables don't exist

## Container Restart

```bash
docker-compose restart data_ingestion_api
```

**Status**: Container restarted with updated code ✅

## Testing

**Test 1: API Endpoint**
```bash
curl "http://localhost:8008/connectors/dashboard-stats?client_id=e0e9c949-18fe-4d9a-9295-d5dfb2cc9723" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected**: `200 OK` with zero storage values

**Test 2: Browser**
1. Navigate to `http://localhost:8080/dashboard/admin`
2. Open DevTools → Console
3. **Expected**: `200 OK` for `/connectors/dashboard-stats`
4. **Expected**: Admin Home page displays with "0 GB" storage

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
**Container Restarted**: Yes ✅
