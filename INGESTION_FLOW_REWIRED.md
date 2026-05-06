# Ingestion Flow Rewired - Direct to Column Mapping

## Problem

After creating a BigQuery connector and foreign table, the mapping page showed "Descoberta de colunas pendente" (discovery pending) instead of loading the columns directly for mapping.

## Root Cause

The `create_bigquery_foreign_table` RPC was creating a minimal FDW stub (with just `id` and `_data` columns) but not returning the actual BigQuery columns. The mapping page would then check `client_data_sources.source_columns`, find it empty, and show the discovery pending state.

## Solution: Three-Part Fix

### 1. Database Migration: Enhanced Foreign Table Creation RPC

**File:** `supabase/migrations/20260428160000_fix_bigquery_ft_discover_columns.sql`

**Changes to `create_bigquery_foreign_table` RPC:**

- After creating the minimal foreign table stub, immediately query `information_schema.columns` to discover the actual columns from the FDW
- Populate the discovered columns into the response
- Store `source_columns` in `client_data_sources` table during the RPC execution
- Return `columns` array in the JSON response

**Key code:**

```plpgsql
-- Query information_schema to discover columns
FOR v_col_record IN
  SELECT column_name, data_type, is_nullable, ordinal_position
  FROM information_schema.columns
  WHERE table_schema = 'public'
    AND table_name = v_foreign_table_name
  ORDER BY ordinal_position
LOOP
  -- Build v_col_array with discovered columns
END LOOP;

-- Insert into client_data_sources WITH source_columns populated
INSERT INTO public.client_data_sources (
  ..., source_columns, sync_status, ...
)
VALUES (
  ..., v_col_array, 'discovery_pending', ...  -- source_columns NOW POPULATED
);

-- Return columns in response
RETURN jsonb_build_object(
  'success', true,
  'data_source_id', v_data_source_id,
  'columns', v_col_array,  -- ← RETURN COLUMNS
  ...
);
```

### 2. Frontend Service Update: Handle Returned Columns

**File:** `apps/blu_dashboard/src/services/connectorService.ts` (lines 299-348)

**Changes to `createCredential` function:**

- Updated type annotation for `ftResult` to include `columns?: Array<{ name: string; type: string; nullable?: boolean }>`
- Filter out stub columns (`id`, `_data`) from discovered columns
- Pass real columns to `matchAndSaveColumnMapping` edge function
- Improved logging to show discovery status

**Key code:**

```typescript
const realColumns = ftResult.columns.filter(
  (col) => !["id", "_data"].includes(col.name),
);

if (realColumns.length > 0) {
  const mapping = await matchAndSaveColumnMapping(
    ftResult.data_source_id,
    realColumns,
    "invoices",
  );
  console.log("Column mapping saved:", Object.keys(mapping).length, "mappings");
}
```

### 3. Frontend Mapping Page: Already Configured

**File:** `apps/blu_dashboard/src/pages/admin/AdminConnectorMappingPage.tsx` (no changes needed)

The mapping page already has the correct logic (line 195-205):

```typescript
const hasSourceColumns =
  !!dataSource?.source_columns &&
  (Array.isArray(dataSource.source_columns)
    ? dataSource.source_columns.length > 0
    : Object.keys(dataSource.source_columns).length > 0);

if (!dataSource || !hasSourceColumns) {
  setDiscoveryPending(true); // Only shows if NO source_columns
  return;
}
```

Since `source_columns` is now populated by the RPC, this condition is skipped.

## New Ingestion Flow

```
1. User creates BigQuery connector
   ↓
2. createCredential() → create_bigquery_server RPC
   ↓
3. createCredential() → create_bigquery_foreign_table RPC
   ├─ Creates minimal FDW table
   ├─ Discovers columns from information_schema
   ├─ Populates client_data_sources.source_columns
   ├─ Returns columns[] in response
   ↓
4. connectorService filters stub columns
   ↓
5. connectorService → matchAndSaveColumnMapping() edge function
   ├─ Matches BigQuery columns to canonical schema
   ├─ Saves column_mapping to client_data_sources
   ↓
6. User navigates to mapping page
   ↓
7. Mapping page loads client_data_sources
   ├─ Finds source_columns ✓
   ├─ Finds column_mapping ✓
   ├─ SKIPS discovery_pending state ✓
   ├─ Shows column mapping interface
   ↓
8. User reviews & confirms mapping
   ↓
9. User clicks "Confirmar e Sincronizar"
   ↓
10. Sync job runs (run-sync-etl edge function)
    └─ Loads data from BigQuery into canonical tables
```

## Console Indicators

After the fix, you should see:

```
Foreign table created successfully: <uuid>
Discovered columns: <N>
Column mapping saved: <N> mappings
```

Then navigate directly to the mapping page - it should show the columns immediately without the discovery pending state.

## Deployment Steps

1. Apply the migration: `supabase migration up`
2. Deploy frontend with updated `connectorService.ts`
3. Test new connector creation flow

## Rollback (if needed)

If issues arise, the RPC is backward-compatible. The mapping page can still handle the discovery_pending state and will trigger discovery async via the edge function if needed.
