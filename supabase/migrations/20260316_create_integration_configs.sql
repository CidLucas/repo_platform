-- Migration: Create integration_configs table
-- Purpose: Store encrypted OAuth client credentials per client/provider
-- Date: 2026-03-16

CREATE TABLE IF NOT EXISTS public.integration_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client isolation
    client_id UUID NOT NULL REFERENCES clientes_vizu(client_id) ON DELETE CASCADE,

    -- Provider identification
    provider TEXT NOT NULL,
    config_type TEXT NOT NULL,

    -- Encrypted OAuth client credentials (encrypted by application layer)
    client_id_encrypted TEXT NOT NULL,
    client_secret_encrypted TEXT NOT NULL,

    -- Public configuration
    redirect_uri TEXT NOT NULL,
    scopes JSONB DEFAULT '[]'::JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Composite unique constraint (used by Supabase upsert on_conflict)
CREATE UNIQUE INDEX uq_integration_configs_client_provider_type
ON integration_configs(client_id, provider, config_type);

-- Lookup indexes
CREATE INDEX idx_integration_configs_client ON integration_configs(client_id);
CREATE INDEX idx_integration_configs_provider ON integration_configs(provider);

-- RLS Policies
ALTER TABLE integration_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own integration configs"
ON integration_configs
FOR SELECT
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Users can insert own integration configs"
ON integration_configs
FOR INSERT
WITH CHECK (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Users can update own integration configs"
ON integration_configs
FOR UPDATE
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Users can delete own integration configs"
ON integration_configs
FOR DELETE
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Service role has full access to integration configs"
ON integration_configs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
