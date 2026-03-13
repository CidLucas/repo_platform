-- Migration: Create standalone_agent_sessions table
-- Purpose: Track user sessions for standalone agents (config state, uploads, context)
-- Date: 2026-03-11

CREATE TABLE IF NOT EXISTS public.standalone_agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client isolation
    client_id UUID NOT NULL REFERENCES clientes_vizu(client_id) ON DELETE CASCADE,

    -- Which agent type this session uses
    agent_catalog_id UUID NOT NULL REFERENCES agent_catalog(id) ON DELETE RESTRICT,

    -- Links to LangGraph thread_id / Redis checkpointer
    session_id TEXT NOT NULL UNIQUE,

    -- Configuration lifecycle
    config_status TEXT DEFAULT 'configuring'
        CHECK (config_status IN ('configuring', 'ready', 'active', 'archived')),

    -- Key-value pairs gathered by config helper
    collected_context JSONB DEFAULT '{}'::JSONB,

    -- References to uploaded CSV files (uploaded_files_metadata.id)
    uploaded_file_ids UUID[] DEFAULT ARRAY[]::UUID[],

    -- References to embedded documents (vector_db.documents.id)
    uploaded_document_ids UUID[] DEFAULT ARRAY[]::UUID[],

    -- Google account linked to this session
    google_account_email TEXT,

    -- Extra metadata
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_standalone_sessions_client ON standalone_agent_sessions(client_id);
CREATE INDEX idx_standalone_sessions_catalog ON standalone_agent_sessions(agent_catalog_id);
CREATE INDEX idx_standalone_sessions_status ON standalone_agent_sessions(config_status);
CREATE INDEX idx_standalone_sessions_session_id ON standalone_agent_sessions(session_id);

-- RLS Policies
ALTER TABLE standalone_agent_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view their own sessions
CREATE POLICY "Users can view own standalone sessions"
ON standalone_agent_sessions
FOR SELECT
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Users can create their own sessions
CREATE POLICY "Users can insert own standalone sessions"
ON standalone_agent_sessions
FOR INSERT
WITH CHECK (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Users can update their own sessions
CREATE POLICY "Users can update own standalone sessions"
ON standalone_agent_sessions
FOR UPDATE
USING (
    client_id IN (
        SELECT client_id FROM clientes_vizu
        WHERE external_user_id = auth.jwt() ->> 'sub'
    )
);

-- Policy: Service role has full access
CREATE POLICY "Service role has full access to standalone sessions"
ON standalone_agent_sessions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
