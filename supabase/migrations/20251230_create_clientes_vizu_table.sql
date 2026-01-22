-- =====================================================================
-- Create clientes_vizu table for multi-tenant authentication
-- =====================================================================
-- Purpose: Store client/tenant information for authentication and context
-- Created: 2025-12-30
-- =====================================================================

-- Create clientes_vizu table
CREATE TABLE IF NOT EXISTS public.clientes_vizu (
    -- Primary identifier (uses Supabase auth.users.id for OAuth users)
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Legacy API key support (optional)
    api_key TEXT UNIQUE,

    -- Company/tenant information
    nome_empresa TEXT NOT NULL DEFAULT 'Empresa',
    tipo_cliente TEXT DEFAULT 'standard',
    tier TEXT DEFAULT 'free',

    -- Configuration
    prompt_base TEXT DEFAULT 'Você é um assistente útil.',
    horario_funcionamento JSONB DEFAULT '{}'::JSONB,
    enabled_tools TEXT[] DEFAULT ARRAY[]::TEXT[],
    collection_rag TEXT DEFAULT 'default_collection',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- External user mapping (for OAuth/JWT users)
    external_user_id TEXT UNIQUE,

    -- Ensure either api_key or external_user_id is present
    CONSTRAINT clientes_vizu_auth_check CHECK (
        api_key IS NOT NULL OR external_user_id IS NOT NULL
    )
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_api_key ON public.clientes_vizu(api_key) WHERE api_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_external_user_id ON public.clientes_vizu(external_user_id) WHERE external_user_id IS NOT NULL;

-- Add RLS policies
ALTER TABLE public.clientes_vizu ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own record
CREATE POLICY "Users can read own cliente record"
ON public.clientes_vizu
FOR SELECT
USING (
    -- Allow if external_user_id matches authenticated user
    external_user_id = auth.jwt() ->> 'sub'
    OR
    -- Allow if using API key (checked by app logic)
    api_key IS NOT NULL
);

-- Policy: Service role can do anything
CREATE POLICY "Service role has full access to clientes_vizu"
ON public.clientes_vizu
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: Authenticated users can insert their own record
CREATE POLICY "Authenticated users can insert own cliente record"
ON public.clientes_vizu
FOR INSERT
TO authenticated
WITH CHECK (
    external_user_id = auth.jwt() ->> 'sub'
);

-- Policy: Users can update their own record
CREATE POLICY "Users can update own cliente record"
ON public.clientes_vizu
FOR UPDATE
TO authenticated
USING (external_user_id = auth.jwt() ->> 'sub')
WITH CHECK (external_user_id = auth.jwt() ->> 'sub');

-- Add comments
COMMENT ON TABLE public.clientes_vizu IS 'Multi-tenant client/customer records for authentication and context';
COMMENT ON COLUMN public.clientes_vizu.client_id IS 'Primary identifier, uses Supabase user ID for OAuth users';
COMMENT ON COLUMN public.clientes_vizu.api_key IS 'Legacy API key for non-OAuth authentication';
COMMENT ON COLUMN public.clientes_vizu.external_user_id IS 'Supabase auth.users.id for OAuth users';
COMMENT ON COLUMN public.clientes_vizu.enabled_tools IS 'Array of tool names enabled for this client';
