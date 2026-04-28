-- =============================================================================
-- Migration: Phase 5 — Core functions and helper RPCs baseline
-- Date: 2026-04-28
-- Purpose: Create tenant context, onboarding, and audit helper functions
-- =============================================================================

BEGIN;

-- ============================================================================
-- 5.1 Tenant Resolution Helpers
-- ============================================================================

-- Resolves current user's client_id via JWT external_user_id claim
CREATE OR REPLACE FUNCTION public.get_my_client_id()
RETURNS UUID LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public AS $$
  SELECT client_id FROM public.clientes_blu
  WHERE external_user_id = auth.uid()::text
  LIMIT 1;
$$;

-- Idempotent: creates clientes_blu row on first login
CREATE OR REPLACE FUNCTION public.ensure_tenant_row()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_user_id text := auth.uid()::text;
  v_email   text;
  v_client_id uuid;
BEGIN
  SELECT client_id INTO v_client_id FROM public.clientes_blu
  WHERE external_user_id = v_user_id;
  IF v_client_id IS NULL THEN
    SELECT email INTO v_email FROM auth.users WHERE id = auth.uid();
    INSERT INTO public.clientes_blu (external_user_id, nome_empresa)
    VALUES (v_user_id, COALESCE(v_email, 'Empresa'))
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;
  END IF;
  RETURN jsonb_build_object('client_id', v_client_id);
END;
$$;

-- RLS context setter for service-role callers
CREATE OR REPLACE FUNCTION public.set_current_cliente_id(p_client_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;
$$;

-- ============================================================================
-- 5.2 Onboarding Functions
-- ============================================================================

-- Race-free JSONB patch merge into clientes_blu.onboarding_state
CREATE OR REPLACE FUNCTION public.merge_onboarding_state(p_patch jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_result    jsonb;
BEGIN
  UPDATE public.clientes_blu
  SET onboarding_state = onboarding_state || p_patch,
      updated_at       = now()
  WHERE client_id = v_client_id
  RETURNING onboarding_state INTO v_result;
  RETURN v_result;
END;
$$;

-- Atomic tenant provisioning (called by onboarding-bootstrap edge fn)
CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx(p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public, pg_temp AS $$
DECLARE
  v_client_id   uuid := public.get_my_client_id();
  v_agent_slug  text;
  v_routine_id  text;
  v_agents_ct   integer := 0;
  v_routines_ct integer := 0;
  v_notify      text;
BEGIN
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant row found for current user';
  END IF;

  v_notify := COALESCE(p_payload->>'notify_channel', 'app');

  -- Update Context 2.0 sections + mark onboarding complete (idempotent)
  UPDATE public.clientes_blu SET
    nome_empresa            = COALESCE(p_payload->>'nome_empresa', nome_empresa),
    company_profile         = COALESCE(p_payload->'company_profile', company_profile),
    team_structure          = COALESCE(p_payload->'team_structure', team_structure),
    policies                = COALESCE(p_payload->'policies', policies),
    onboarding_completed_at = COALESCE(onboarding_completed_at, now()),
    updated_at              = now()
  WHERE client_id = v_client_id;

  -- Enable requested agents
  FOR v_agent_slug IN SELECT jsonb_array_elements_text(p_payload->'agents') LOOP
    INSERT INTO public.client_enabled_agents (client_id, agent_slug)
    VALUES (v_client_id, v_agent_slug)
    ON CONFLICT (client_id, agent_slug) DO NOTHING;
    v_agents_ct := v_agents_ct + 1;
  END LOOP;

  -- Enable requested routines
  FOR v_routine_id IN SELECT jsonb_array_elements_text(p_payload->'routines') LOOP
    INSERT INTO public.client_routines (client_id, routine_id, notify_channel)
    VALUES (v_client_id, v_routine_id, v_notify)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET notify_channel = EXCLUDED.notify_channel;
    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;
$$;

-- ============================================================================
-- 5.3 KPI Catalog Functions
-- ============================================================================

CREATE OR REPLACE FUNCTION public.list_kpi_catalog(
  p_dimension   text DEFAULT NULL,
  p_only_enabled boolean DEFAULT false
)
RETURNS TABLE (
  slug text, dimension text, label text, unit text,
  data_status text, sort_order int, is_default boolean,
  default_dimension_rank int, is_enabled boolean
) LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT
    k.slug, k.dimension, k.label, k.unit, k.data_status, k.sort_order,
    false AS is_default,
    NULL::int AS default_dimension_rank,
    (EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id()
        AND ck.slug = k.slug
    )) AS is_enabled
  FROM public.kpi_catalog k
  WHERE (p_dimension IS NULL OR k.dimension = p_dimension)
    AND (NOT p_only_enabled OR EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id() AND ck.slug = k.slug
    ))
  ORDER BY k.sort_order, k.slug;
$$;

CREATE OR REPLACE FUNCTION public.set_client_dimension_kpis(
  p_dimension text,
  p_slugs     text[]
)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
BEGIN
  DELETE FROM public.client_dimension_kpis
  WHERE client_id = v_client_id AND dimension = p_dimension;

  INSERT INTO public.client_dimension_kpis (client_id, dimension, slug)
  SELECT v_client_id, p_dimension, s
  FROM unnest(p_slugs) s
  WHERE EXISTS (SELECT 1 FROM public.kpi_catalog WHERE slug = s)
  ON CONFLICT DO NOTHING;

  RETURN jsonb_build_object('dimension', p_dimension, 'count', array_length(p_slugs, 1));
END;
$$;

-- ============================================================================
-- 5.4 Audit & Approval Functions
-- ============================================================================

CREATE OR REPLACE FUNCTION public.record_audit(
  p_action      text,
  p_entity_type text DEFAULT NULL,
  p_entity_id   text DEFAULT NULL,
  p_payload     jsonb DEFAULT '{}'
)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO public.audit_log (client_id, actor_id, action, entity_type, entity_id, payload)
  VALUES (public.get_my_client_id(), auth.uid()::text, p_action, p_entity_type, p_entity_id, p_payload);
END;
$$;

CREATE OR REPLACE FUNCTION public.request_approval(
  p_action_type text,
  p_payload     jsonb DEFAULT '{}',
  p_expires_at  timestamptz DEFAULT NULL
)
RETURNS uuid LANGUAGE plpgsql SECURITY INVOKER AS $$
DECLARE v_id uuid;
BEGIN
  INSERT INTO public.approval_requests
    (client_id, requested_by, action_type, payload, expires_at)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, p_action_type, p_payload, p_expires_at)
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.decide_approval(
  p_request_id uuid,
  p_decision   text,
  p_reason     text DEFAULT NULL
)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  UPDATE public.approval_requests
  SET status     = p_decision,
      decided_by = auth.uid()::text,
      decided_at = now(),
      payload    = payload || jsonb_build_object('reason', p_reason)
  WHERE id = p_request_id
    AND client_id = public.get_my_client_id()
    AND status = 'pending';

  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'Not found or already decided');
  END IF;
  RETURN jsonb_build_object('success', true, 'status', p_decision);
END;
$$;

CREATE OR REPLACE FUNCTION public.list_pending_approvals()
RETURNS SETOF public.approval_requests LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT * FROM public.approval_requests
  WHERE client_id = public.get_my_client_id()
    AND status = 'pending'
    AND (expires_at IS NULL OR expires_at > now())
  ORDER BY created_at DESC;
$$;

-- ============================================================================
-- 5.5 Frontend Events
-- ============================================================================

CREATE OR REPLACE FUNCTION public.record_frontend_event(
  p_event_name text,
  p_properties jsonb DEFAULT '{}'
)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  INSERT INTO public.frontend_events (client_id, event_name, properties)
  VALUES (public.get_my_client_id(), p_event_name, p_properties);
END;
$$;

-- ============================================================================
-- 5.6 Insight Management
-- ============================================================================

CREATE OR REPLACE FUNCTION public.dismiss_insight(p_insight_id uuid)
RETURNS void LANGUAGE sql SECURITY INVOKER AS $$
  UPDATE public.client_insights
  SET dismissed = true, dismissed_at = now()
  WHERE id = p_insight_id
    AND client_id = public.get_my_client_id();
$$;

-- ============================================================================
-- 5.7 RAG — Hybrid Search
-- ============================================================================

CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(
  p_client_id    uuid,
  p_query_embed  extensions.halfvec(384),
  p_query_text   text,
  p_match_count  int     DEFAULT 10,
  p_theme_filter text    DEFAULT NULL
)
RETURNS TABLE (
  id          integer,
  document_id uuid,
  content     text,
  metadata    jsonb,
  similarity  float
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  WITH semantic AS (
    SELECT
      c.id, c.document_id, c.content, c.metadata,
      1 - (c.embedding <#> p_query_embed) AS sim
    FROM vector_db.document_chunks c
    WHERE c.client_id = p_client_id
      AND (p_theme_filter IS NULL OR c.metadata->>'theme' = p_theme_filter)
    ORDER BY c.embedding <#> p_query_embed
    LIMIT p_match_count * 3
  ),
  fts AS (
    SELECT
      c.id, c.document_id, c.content, c.metadata,
      ts_rank(c.fts, plainto_tsquery('portuguese', p_query_text)) AS rank
    FROM vector_db.document_chunks c
    WHERE c.client_id = p_client_id
      AND c.fts @@ plainto_tsquery('portuguese', p_query_text)
      AND (p_theme_filter IS NULL OR c.metadata->>'theme' = p_theme_filter)
    LIMIT p_match_count * 3
  )
  SELECT DISTINCT ON (COALESCE(s.id, f.id))
    COALESCE(s.id, f.id),
    COALESCE(s.document_id, f.document_id),
    COALESCE(s.content, f.content),
    COALESCE(s.metadata, f.metadata),
    COALESCE(s.sim, 0) * 0.7 + COALESCE(f.rank, 0) * 0.3 AS similarity
  FROM semantic s
  FULL OUTER JOIN fts f USING (id)
  ORDER BY COALESCE(s.id, f.id), similarity DESC
  LIMIT p_match_count;
$$;

-- ============================================================================
-- 5.8 Google OAuth Config Helper
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_platform_google_oauth_config()
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT decrypted_secret::jsonb FROM vault.decrypted_secrets
  WHERE name = 'google_oauth_config' LIMIT 1;
$$;

COMMIT;
