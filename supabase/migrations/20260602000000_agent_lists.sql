-- =============================================================================
-- Migration: agent_lists
-- Purpose: Generic persistent list store for agent operations.
--   Replaces ad-hoc tables (rfq_requests, supplier_roster, etc.) with a
--   single flexible table keyed by list_type. Each agent/operation owns its
--   own namespace via list_type; items and metadata are free-form JSONB.
--
-- Design decisions:
--   - list_type: namespaces the table (e.g. 'rfq', 'buying_list', 'checklist')
--   - items: array of JSONB objects (ordered, appendable)
--   - metadata: arbitrary key/value bag per list (deadlines, references, etc.)
--   - status: open | active | closed | cancelled (generic lifecycle)
--   - created_by: agent slug that created the list (observability)
--   - session_id: optional link to the agent session that originated the list
--   - RLS: each client sees only their own rows (client_id isolation)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.agent_lists (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   uuid NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
    list_type   text NOT NULL,          -- e.g. 'rfq', 'buying_list', 'approval_queue'
    name        text,                   -- human-readable label (optional)
    items       jsonb NOT NULL DEFAULT '[]'::jsonb,   -- ordered array of item objects
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,   -- arbitrary extra fields
    status      text NOT NULL DEFAULT 'open'          -- open | active | closed | cancelled
                    CHECK (status IN ('open', 'active', 'closed', 'cancelled')),
    created_by  text,                   -- agent slug (e.g. 'compras', 'data-entry')
    session_id  text,                   -- originating agent session (optional)
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Fast lookup by tenant + type (most common query pattern)
CREATE INDEX idx_agent_lists_client_type
    ON public.agent_lists (client_id, list_type);

-- Fast lookup by session (RFQ status checks, session-scoped lists)
CREATE INDEX idx_agent_lists_session
    ON public.agent_lists (client_id, session_id)
    WHERE session_id IS NOT NULL;

-- Status filter (e.g. all open RFQs for a client)
CREATE INDEX idx_agent_lists_status
    ON public.agent_lists (client_id, list_type, status);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_agent_lists_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_agent_lists_updated_at
    BEFORE UPDATE ON public.agent_lists
    FOR EACH ROW EXECUTE FUNCTION public.set_agent_lists_updated_at();

-- RLS: tenants see only their own lists
ALTER TABLE public.agent_lists ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_lists_tenant_isolation ON public.agent_lists
    USING (client_id = (current_setting('app.current_client_id', true))::uuid);

-- Service-role bypass (tool_pool_api uses service_role key)
CREATE POLICY agent_lists_service_role ON public.agent_lists
    TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.agent_lists IS
    'Generic persistent list store for agent operations. '
    'Keyed by list_type — each agent/operation owns its namespace. '
    'Replaces: rfq_requests. Future: buying_list, approval_queue, checklist.';
