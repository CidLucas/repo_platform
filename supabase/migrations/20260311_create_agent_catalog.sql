-- Migration: Create agent_catalog table
-- Purpose: Catalog of available standalone agent types with their configurations
-- Date: 2026-03-11

CREATE TABLE IF NOT EXISTS public.agent_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Agent identity
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT,
    icon TEXT,

    -- Agent configuration (maps 1:1 to AgentConfig dataclass)
    -- Fields: name, role, elicitation_strategy, enabled_tools, max_turns, model, metadata
    agent_config JSONB NOT NULL,

    -- Langfuse prompt path (e.g., 'standalone/data-analyst')
    prompt_name TEXT NOT NULL,

    -- Fields the Config Helper must collect from the user
    -- Format: [{field, type, required, label, prompt_hint}]
    required_context JSONB DEFAULT '[]'::JSONB,

    -- File requirements per type
    -- Format: {csv: {min, max, description}, text: {min, max, description}}
    required_files JSONB DEFAULT '{}'::JSONB,

    -- Integration requirements
    requires_google BOOLEAN DEFAULT false,

    -- Access control
    tier_required TEXT DEFAULT 'BASIC',

    -- Lifecycle
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_agent_catalog_slug ON agent_catalog(slug);
CREATE INDEX idx_agent_catalog_category ON agent_catalog(category);
CREATE INDEX idx_agent_catalog_active ON agent_catalog(is_active) WHERE is_active = true;

-- RLS Policies
ALTER TABLE agent_catalog ENABLE ROW LEVEL SECURITY;

-- Policy: All authenticated users can view active agents
CREATE POLICY "Authenticated users can view active agents"
ON agent_catalog
FOR SELECT
TO authenticated
USING (is_active = true);

-- Policy: Service role has full access (for seeding and admin operations)
CREATE POLICY "Service role has full access to agent catalog"
ON agent_catalog
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
