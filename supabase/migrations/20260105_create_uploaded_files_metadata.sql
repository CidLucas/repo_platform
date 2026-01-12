-- Migration: Create uploaded_files_metadata table
-- Purpose: Track CSV/Excel files uploaded by clients with processing status and storage references
-- Date: 2026-01-05

CREATE TABLE IF NOT EXISTS public.uploaded_files_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client isolation
    client_id UUID NOT NULL REFERENCES clientes_vizu(id) ON DELETE CASCADE,

    -- File information
    file_name TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_type TEXT, -- 'csv', 'xlsx', etc.
    content_type TEXT,

    -- Storage location
    storage_bucket TEXT DEFAULT 'file-uploads',
    storage_path TEXT NOT NULL, -- Full path in Supabase Storage

    -- Processing status
    status TEXT DEFAULT 'uploaded'
        CHECK (status IN ('uploaded', 'processing', 'completed', 'failed', 'deleted')),

    -- Metrics
    records_count INTEGER DEFAULT 0,
    records_imported INTEGER DEFAULT 0,

    -- Error handling
    error_message TEXT,

    -- Timestamps
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_uploaded_files_cliente ON uploaded_files_metadata(client_id);
CREATE INDEX idx_uploaded_files_status ON uploaded_files_metadata(status);
CREATE INDEX idx_uploaded_files_uploaded_at ON uploaded_files_metadata(uploaded_at DESC);

-- RLS Policies
ALTER TABLE uploaded_files_metadata ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view their own files
CREATE POLICY "Users can view own uploaded files"
ON uploaded_files_metadata
FOR SELECT
USING (
    client_id IN (
        SELECT id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Users can insert their own files
CREATE POLICY "Users can insert own uploaded files"
ON uploaded_files_metadata
FOR INSERT
WITH CHECK (
    client_id IN (
        SELECT id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Users can update their own files
CREATE POLICY "Users can update own uploaded files"
ON uploaded_files_metadata
FOR UPDATE
USING (
    client_id IN (
        SELECT id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Users can delete their own files
CREATE POLICY "Users can delete own uploaded files"
ON uploaded_files_metadata
FOR DELETE
USING (
    client_id IN (
        SELECT id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Service role has full access
CREATE POLICY "Service role has full access to uploaded files"
ON uploaded_files_metadata
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_uploaded_files_metadata_updated_at
    BEFORE UPDATE ON uploaded_files_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_connector_sync_history_updated_at();

-- Comments
COMMENT ON TABLE uploaded_files_metadata IS 'Tracks CSV/Excel files uploaded by clients with processing status and storage references';
COMMENT ON COLUMN uploaded_files_metadata.client_id IS 'Foreign key to clientes_vizu for multi-tenant isolation';
COMMENT ON COLUMN uploaded_files_metadata.storage_path IS 'Full path to file in Supabase Storage bucket';
COMMENT ON COLUMN uploaded_files_metadata.status IS 'Processing status: uploaded, processing, completed, failed, or deleted';
COMMENT ON COLUMN uploaded_files_metadata.records_count IS 'Total number of records in the file';
COMMENT ON COLUMN uploaded_files_metadata.records_imported IS 'Number of records successfully imported to database';
