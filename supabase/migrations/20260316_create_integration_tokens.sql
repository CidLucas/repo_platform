-- Migration: Create integration_tokens table
-- Purpose: Store encrypted OAuth tokens per client/provider/account (multi-account support)
-- Date: 2026-03-16

CREATE TABLE IF NOT EXISTS public.integration_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client isolation
    client_id UUID NOT NULL REFERENCES clientes_vizu(client_id) ON DELETE CASCADE,

    -- Provider identification
    provider TEXT NOT NULL,

    -- Encrypted OAuth tokens (encrypted by application layer via Fernet)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,

    -- Token metadata
    token_type TEXT,
    expires_at TIMESTAMPTZ,
    scopes JSONB DEFAULT '[]'::JSONB,

    -- Multi-account support
    account_email TEXT NOT NULL DEFAULT 'default@unknown.com',
    account_name TEXT,
    is_default BOOLEAN DEFAULT false,

    -- Extra metadata (non-sensitive, not encrypted)
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Composite unique constraint for upsert (client + provider + account)
CREATE UNIQUE INDEX uq_integration_tokens_client_provider_email
ON integration_tokens(client_id, provider, account_email);

-- Lookup indexes
CREATE INDEX idx_integration_tokens_client ON integration_tokens(client_id);
CREATE INDEX idx_integration_tokens_provider ON integration_tokens(provider);
CREATE INDEX idx_integration_tokens_default ON integration_tokens(client_id, provider, is_default)
    WHERE is_default = true;

-- RLS Policies
ALTER TABLE integration_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own integration tokens"
ON integration_tokens
FOR SELECT
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Users can insert own integration tokens"
ON integration_tokens
FOR INSERT
WITH CHECK (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Users can update own integration tokens"
ON integration_tokens
FOR UPDATE
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Users can delete own integration tokens"
ON integration_tokens
FOR DELETE
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

CREATE POLICY "Service role has full access to integration tokens"
ON integration_tokens
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
