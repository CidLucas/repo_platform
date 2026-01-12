-- Migration: Create connector_sync_history table
-- Purpose: Track sync operations for each data connector with metrics and error handling
-- Date: 2026-01-05

CREATE TABLE IF NOT EXISTS public.connector_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to credencial_servico_externo
    credential_id INTEGER NOT NULL REFERENCES credencial_servico_externo(id) ON DELETE CASCADE,

    -- Sync metadata
    sync_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_completed_at TIMESTAMPTZ,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),

    -- Metrics
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,

    -- Error handling
    error_message TEXT,
    error_details JSONB,

    -- Resource type (products, orders, customers, etc.)
    resource_type TEXT,

    -- Additional metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_sync_history_credential ON connector_sync_history(credential_id);
CREATE INDEX idx_sync_history_status ON connector_sync_history(status);
CREATE INDEX idx_sync_history_completed ON connector_sync_history(sync_completed_at DESC);

-- RLS Policies (multi-tenant isolation)
ALTER TABLE connector_sync_history ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view sync history for their credentials
CREATE POLICY "Users can view own sync history"
ON connector_sync_history
FOR SELECT
USING (
    credential_id IN (
        SELECT id FROM credencial_servico_externo
        WHERE client_id IN (
            SELECT id FROM clientes_vizu
            WHERE external_user_id = auth.jwt() ->> 'sub'
        )
    )
);

-- Policy: Service role has full access
CREATE POLICY "Service role has full access to sync history"
ON connector_sync_history
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_connector_sync_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_connector_sync_history_updated_at
    BEFORE UPDATE ON connector_sync_history
    FOR EACH ROW
    EXECUTE FUNCTION update_connector_sync_history_updated_at();

-- Comments
COMMENT ON TABLE connector_sync_history IS 'Tracks sync operations for data connectors with metrics and error handling';
COMMENT ON COLUMN connector_sync_history.credential_id IS 'Foreign key to credencial_servico_externo table';
COMMENT ON COLUMN connector_sync_history.records_processed IS 'Total number of records processed in this sync';
COMMENT ON COLUMN connector_sync_history.records_inserted IS 'Number of records successfully inserted';
COMMENT ON COLUMN connector_sync_history.records_failed IS 'Number of records that failed to process';
COMMENT ON COLUMN connector_sync_history.status IS 'Sync status: running, completed, failed, or cancelled';
COMMENT ON COLUMN connector_sync_history.resource_type IS 'Type of resource being synced (products, orders, customers, etc.)';
