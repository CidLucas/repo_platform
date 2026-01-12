-- ============================================================================
-- CREATE MISSING TABLES FOR data_ingestion_api
-- Run this in Supabase SQL Editor
-- ============================================================================

-- Table 1: uploaded_files_metadata
-- Purpose: Track CSV/Excel files uploaded by users
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.uploaded_files_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES public.clientes_vizu(id) ON DELETE CASCADE,

    -- File information
    file_name TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    file_type TEXT, -- 'csv', 'excel', etc.

    -- Storage location (Supabase Storage)
    storage_bucket TEXT DEFAULT 'vizu-uploads',
    storage_path TEXT NOT NULL,

    -- Processing status
    status TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'completed', 'failed', 'deleted')),

    -- Data metrics
    records_count INTEGER DEFAULT 0,
    records_imported INTEGER DEFAULT 0,
    error_message TEXT,

    -- Timestamps
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_uploaded_files_client_id
    ON public.uploaded_files_metadata(client_id);

CREATE INDEX IF NOT EXISTS idx_uploaded_files_status
    ON public.uploaded_files_metadata(status);

CREATE INDEX IF NOT EXISTS idx_uploaded_files_uploaded_at
    ON public.uploaded_files_metadata(uploaded_at DESC);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION public.update_uploaded_files_metadata_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_uploaded_files_metadata_updated_at
    BEFORE UPDATE ON public.uploaded_files_metadata
    FOR EACH ROW
    EXECUTE FUNCTION public.update_uploaded_files_metadata_updated_at();

-- Enable Row Level Security (RLS)
ALTER TABLE public.uploaded_files_metadata ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own files
CREATE POLICY "Users can view their own uploaded files"
    ON public.uploaded_files_metadata
    FOR SELECT
    USING (
        client_id IN (
            SELECT id FROM public.clientes_vizu
            WHERE user_id = auth.uid()
        )
    );

-- RLS Policy: Users can insert their own files
CREATE POLICY "Users can insert their own uploaded files"
    ON public.uploaded_files_metadata
    FOR INSERT
    WITH CHECK (
        client_id IN (
            SELECT id FROM public.clientes_vizu
            WHERE user_id = auth.uid()
        )
    );

-- RLS Policy: Users can update their own files
CREATE POLICY "Users can update their own uploaded files"
    ON public.uploaded_files_metadata
    FOR UPDATE
    USING (
        client_id IN (
            SELECT id FROM public.clientes_vizu
            WHERE user_id = auth.uid()
        )
    );

-- RLS Policy: Users can delete (soft delete) their own files
CREATE POLICY "Users can delete their own uploaded files"
    ON public.uploaded_files_metadata
    FOR DELETE
    USING (
        client_id IN (
            SELECT id FROM public.clientes_vizu
            WHERE user_id = auth.uid()
        )
    );

-- Service role bypass (for backend services)
CREATE POLICY "Service role has full access to uploaded files"
    ON public.uploaded_files_metadata
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');


-- ============================================================================
-- Table 2: connector_sync_history
-- Purpose: Track sync operations for each data connector
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.connector_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id INTEGER NOT NULL REFERENCES public.credencial_servico_externo(id) ON DELETE CASCADE,

    -- Sync status
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),

    -- Sync timing
    sync_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sync_completed_at TIMESTAMPTZ,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN sync_completed_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (sync_completed_at - sync_started_at))::INTEGER
            ELSE NULL
        END
    ) STORED,

    -- Data metrics
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,

    -- Resource type being synced (optional - for granular tracking)
    resource_type TEXT, -- 'products', 'orders', 'customers', etc.

    -- Error details
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sync_history_credential_id
    ON public.connector_sync_history(credential_id);

CREATE INDEX IF NOT EXISTS idx_sync_history_status
    ON public.connector_sync_history(status);

CREATE INDEX IF NOT EXISTS idx_sync_history_started_at
    ON public.connector_sync_history(sync_started_at DESC);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION public.update_connector_sync_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_connector_sync_history_updated_at
    BEFORE UPDATE ON public.connector_sync_history
    FOR EACH ROW
    EXECUTE FUNCTION public.update_connector_sync_history_updated_at();

-- Enable Row Level Security (RLS)
ALTER TABLE public.connector_sync_history ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view sync history for their own connectors
CREATE POLICY "Users can view their own connector sync history"
    ON public.connector_sync_history
    FOR SELECT
    USING (
        credential_id IN (
            SELECT cse.id
            FROM public.credencial_servico_externo cse
            JOIN public.clientes_vizu cv ON cse.client_id = cv.id
            WHERE cv.user_id = auth.uid()
        )
    );

-- RLS Policy: Service role can insert sync records
CREATE POLICY "Service role can insert sync history"
    ON public.connector_sync_history
    FOR INSERT
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- RLS Policy: Service role can update sync records
CREATE POLICY "Service role can update sync history"
    ON public.connector_sync_history
    FOR UPDATE
    USING (auth.jwt()->>'role' = 'service_role');

-- Service role bypass (for backend services)
CREATE POLICY "Service role has full access to sync history"
    ON public.connector_sync_history
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');


-- ============================================================================
-- OPTIONAL: analytics_silver table
-- Only create if you plan to use a separate analytics storage layer
-- Currently the code uses existing analytics tables, so this is OPTIONAL
-- ============================================================================

/*
CREATE TABLE IF NOT EXISTS public.analytics_silver (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES public.clientes_vizu(id) ON DELETE CASCADE,

    -- Data columns (customize based on your needs)
    entity_type TEXT NOT NULL, -- 'product', 'order', 'customer', etc.
    entity_id TEXT NOT NULL,
    data JSONB NOT NULL,

    -- Metadata
    source_connector_id INTEGER REFERENCES public.credencial_servico_externo(id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_analytics_silver_client_id
    ON public.analytics_silver(client_id);

CREATE INDEX IF NOT EXISTS idx_analytics_silver_entity_type
    ON public.analytics_silver(entity_type);

CREATE INDEX IF NOT EXISTS idx_analytics_silver_ingested_at
    ON public.analytics_silver(ingested_at DESC);

-- RLS
ALTER TABLE public.analytics_silver ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own analytics data"
    ON public.analytics_silver
    FOR SELECT
    USING (
        client_id IN (
            SELECT id FROM public.clientes_vizu
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to analytics"
    ON public.analytics_silver
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');
*/


-- ============================================================================
-- VERIFICATION QUERIES
-- Run these to verify tables were created successfully
-- ============================================================================

-- Check if tables exist
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename IN ('uploaded_files_metadata', 'connector_sync_history', 'analytics_silver')
ORDER BY tablename;

-- Check RLS is enabled
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename IN ('uploaded_files_metadata', 'connector_sync_history')
ORDER BY tablename;

-- Check policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE tablename IN ('uploaded_files_metadata', 'connector_sync_history')
ORDER BY tablename, policyname;

-- Count records (should be 0 for new tables)
SELECT 'uploaded_files_metadata' as table_name, COUNT(*) as record_count FROM public.uploaded_files_metadata
UNION ALL
SELECT 'connector_sync_history', COUNT(*) FROM public.connector_sync_history;
