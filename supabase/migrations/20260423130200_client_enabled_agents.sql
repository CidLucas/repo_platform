-- Migration: client_enabled_agents — per-tenant enabled agent registry
-- Phase: Landing Onboarding Wire-up, Phase 1 (Foundation)
-- Date: 2026-04-23
--
-- Source of truth for "which agents does this client have". Written by the
-- onboarding-bootstrap edge function at LaunchPad, read by the dashboard
-- agent gallery and downstream agent execution code.

CREATE TABLE IF NOT EXISTS public.client_enabled_agents (
  client_id    uuid        NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  agent_slug   text        NOT NULL REFERENCES public.agent_catalog(slug),
  enabled      boolean     NOT NULL DEFAULT true,
  source       text        NOT NULL DEFAULT 'onboarding'
    CHECK (source IN ('onboarding', 'admin', 'migration')),
  activated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (client_id, agent_slug)
);

COMMENT ON TABLE public.client_enabled_agents IS
  'Per-tenant registry of enabled agents. agent_slug is FK to agent_catalog.slug; '
  'writes happen in the onboarding-bootstrap edge function and the admin agent gallery.';

CREATE INDEX IF NOT EXISTS idx_client_enabled_agents_client
  ON public.client_enabled_agents (client_id) WHERE enabled;

-- RLS -------------------------------------------------------------------------
ALTER TABLE public.client_enabled_agents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS client_enabled_agents_select ON public.client_enabled_agents;
CREATE POLICY client_enabled_agents_select ON public.client_enabled_agents
  FOR SELECT TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_enabled_agents_insert ON public.client_enabled_agents;
CREATE POLICY client_enabled_agents_insert ON public.client_enabled_agents
  FOR INSERT TO authenticated
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_enabled_agents_update ON public.client_enabled_agents;
CREATE POLICY client_enabled_agents_update ON public.client_enabled_agents
  FOR UPDATE TO authenticated
  USING (client_id::text = public.get_my_client_id())
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_enabled_agents_delete ON public.client_enabled_agents;
CREATE POLICY client_enabled_agents_delete ON public.client_enabled_agents
  FOR DELETE TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_enabled_agents_service_role ON public.client_enabled_agents;
CREATE POLICY client_enabled_agents_service_role ON public.client_enabled_agents
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);
