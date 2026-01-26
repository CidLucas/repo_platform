-- Migration: Add unique constraint to fact_sales for incremental UPSERT support
-- Date: 2026-01-26
-- Purpose: Enable ON CONFLICT (client_id, order_id) for incremental updates

-- ============================================================================
-- STEP 1: Add unique constraint on (client_id, order_id)
-- ============================================================================

-- This constraint enables:
-- 1. UPSERT via ON CONFLICT for incremental syncs
-- 2. Prevention of duplicate order entries per client
-- 3. Idempotent data loading (re-running sync won't create duplicates)

-- First, remove any duplicates that might exist
-- Keep the most recent version (by updated_at or created_at)
DELETE FROM analytics_v2.fact_sales a
USING analytics_v2.fact_sales b
WHERE a.client_id = b.client_id
  AND a.order_id = b.order_id
  AND a.sale_id > b.sale_id;  -- Keep the one with lower sale_id (first inserted)

-- Create unique constraint
ALTER TABLE analytics_v2.fact_sales
ADD CONSTRAINT uq_fact_sales_client_order
UNIQUE (client_id, order_id);

-- Create index to support the constraint (if not already exists)
CREATE INDEX IF NOT EXISTS idx_fact_sales_client_order
ON analytics_v2.fact_sales (client_id, order_id);

-- ============================================================================
-- STEP 2: Add last_synced_at column to client_data_sources if not exists
-- ============================================================================

-- Ensure the column exists for tracking incremental sync watermarks
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'client_data_sources'
        AND column_name = 'last_synced_at'
    ) THEN
        ALTER TABLE public.client_data_sources
        ADD COLUMN last_synced_at TIMESTAMPTZ;

        COMMENT ON COLUMN public.client_data_sources.last_synced_at IS
            'Timestamp of last successful sync for this data source. Used for incremental updates.';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Add client_id column to connector_sync_history if not exists
-- ============================================================================

-- Ensure client_id column exists for tracking syncs by client
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'connector_sync_history'
        AND column_name = 'client_id'
    ) THEN
        ALTER TABLE public.connector_sync_history
        ADD COLUMN client_id TEXT;

        CREATE INDEX IF NOT EXISTS idx_connector_sync_history_client_id
        ON public.connector_sync_history (client_id);

        COMMENT ON COLUMN public.connector_sync_history.client_id IS
            'Client ID for this sync event. Used for tracking sync history per client.';
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Create index on data_transacao for incremental queries
-- ============================================================================

-- This index supports WHERE data_transacao > :since_timestamp queries
CREATE INDEX IF NOT EXISTS idx_fact_sales_data_transacao
ON analytics_v2.fact_sales (client_id, data_transacao);

COMMENT ON INDEX analytics_v2.idx_fact_sales_data_transacao IS
    'Supports incremental sync queries filtering by transaction date';
