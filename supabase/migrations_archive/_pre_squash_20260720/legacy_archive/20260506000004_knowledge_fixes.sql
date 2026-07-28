-- ── Knowledge Fix Pack ────────────────────────────────────────────────────────
-- Addresses 4 issues identified in the post-implementation review:
--   1. p_session_id / p_tool_call_id silently discarded by request_approval()
--   2. Never-downgrade guard missing from upsert_client_document()
--   3. Phase 4 on_approval_completed() didn't handle Phase 5 routine actions
--   4. get_agent_readiness() had no tier guard — could show 'ready' for locked agents
--
-- Note on Issue skipped: Phase 5 dispatcher atomicity is already correct.
-- PL/pgSQL BEGIN/EXCEPTION blocks use implicit savepoints; if any step INSERT
-- fails, all prior step INSERTs in the same block are automatically rolled back.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Store session_id and tool_call_id on approval_requests
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.approval_requests
  ADD COLUMN IF NOT EXISTS session_id   text,
  ADD COLUMN IF NOT EXISTS tool_call_id text;

CREATE INDEX IF NOT EXISTS idx_approval_session_id
  ON public.approval_requests (session_id)
  WHERE session_id IS NOT NULL;

-- Replace request_approval to persist the new fields
CREATE OR REPLACE FUNCTION public.request_approval(
  p_action_type     text                     DEFAULT NULL,
  p_payload         jsonb                    DEFAULT '{}'::jsonb,
  p_expires_at      timestamp with time zone DEFAULT NULL,
  p_agent_slug      text                     DEFAULT NULL,
  p_action          text                     DEFAULT NULL,
  p_session_id      text                     DEFAULT NULL,
  p_tool_call_id    text                     DEFAULT NULL,
  p_routed_to_role  text                     DEFAULT NULL,
  p_sla_hours       integer                  DEFAULT 72
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id          uuid;
  v_action_type text := COALESCE(p_action_type, p_action);
  v_expires_at  timestamp with time zone := COALESCE(
    p_expires_at,
    CASE WHEN p_sla_hours IS NOT NULL THEN now() + (p_sla_hours || ' hours')::interval ELSE NULL END
  );
BEGIN
  IF v_action_type IS NULL THEN
    RAISE EXCEPTION 'request_approval: action_type (or p_action) is required';
  END IF;

  INSERT INTO public.approval_requests
    (client_id, requested_by, action_type, agent_slug, payload, expires_at,
     session_id, tool_call_id)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, v_action_type, p_agent_slug,
     p_payload, v_expires_at, p_session_id, p_tool_call_id)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Never-downgrade guard in upsert_client_document()
-- Rule: missing → partial → complete is allowed; reverse is never allowed.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.upsert_client_document(
  p_document_type_id  text,
  p_status            text    DEFAULT 'complete',
  p_source            text    DEFAULT 'upload',
  p_field_coverage    jsonb   DEFAULT '{}',
  p_metadata          jsonb   DEFAULT '{}'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_client_id uuid;
  v_result    jsonb;
BEGIN
  v_client_id := public.get_my_client_id();
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Client not authenticated';
  END IF;

  IF p_status NOT IN ('missing','partial','complete') THEN
    RAISE EXCEPTION 'Invalid status: %. Must be missing | partial | complete', p_status;
  END IF;

  INSERT INTO public.client_knowledge_documents
    (client_id, document_type_id, status, source, field_coverage, metadata, updated_at)
  VALUES
    (v_client_id, p_document_type_id, p_status, p_source, p_field_coverage, p_metadata, now())
  ON CONFLICT (client_id, document_type_id) DO UPDATE SET
    status         = EXCLUDED.status,
    source         = EXCLUDED.source,
    field_coverage = EXCLUDED.field_coverage,
    metadata       = EXCLUDED.metadata,
    updated_at     = now()
  -- Never-downgrade: only update if the new status is >= the existing status.
  -- missing (lowest) → partial → complete (highest); reverse is never allowed.
  WHERE CASE client_knowledge_documents.status
    WHEN 'missing'  THEN true                         -- any status can overwrite missing
    WHEN 'partial'  THEN EXCLUDED.status = 'complete' -- only 'complete' can overwrite partial
    WHEN 'complete' THEN false                        -- nothing overwrites complete
    ELSE true
  END
  RETURNING jsonb_build_object(
    'document_type_id', document_type_id,
    'status',           status,
    'source',           source,
    'updated_at',       updated_at
  ) INTO v_result;

  -- When the WHERE guard prevented the update, RETURNING yields nothing.
  -- Return the current row instead so callers always get a valid response.
  IF v_result IS NULL THEN
    SELECT jsonb_build_object(
      'document_type_id', document_type_id,
      'status',           status,
      'source',           source,
      'updated_at',       updated_at
    ) INTO v_result
    FROM public.client_knowledge_documents
    WHERE client_id = v_client_id AND document_type_id = p_document_type_id;
  END IF;

  RETURN v_result;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Fix on_approval_completed() to handle Phase 5 routine-dispatched actions
--
-- Phase 5 approval_requests are created by process_pending_routine_executions()
-- and carry payload = { routine_id, execution_id, step, expected_output, routine_name }.
--
-- Instead of enumerating action_type strings for every routine step (fragile,
-- and would need updating every time a routine changes), we check for
-- payload→routine_id. If present, expected_output IS the document_type_id.
-- This is forward-compatible with any future routines or step actions.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.on_approval_completed()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_doc_type_id text;
  v_client_id   uuid := NEW.client_id;
BEGIN
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  IF v_client_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Phase 5 routine-dispatched actions carry routine_id in the payload.
  -- Use expected_output directly; no need to map action_type strings.
  IF NEW.payload->>'routine_id' IS NOT NULL THEN
    v_doc_type_id := NEW.payload->>'expected_output';  -- NULL means this step has no output doc
  ELSE
    -- Direct agent actions: map action_type → document_type_id
    v_doc_type_id := CASE NEW.action_type
      WHEN 'create_purchase_order'   THEN 'cotacao_rfq'
      WHEN 'approve_purchase_order'  THEN 'ordem_compra'
      WHEN 'comercial.draft_created' THEN 'proposta_comercial'
      WHEN 'reports.generate'        THEN
        CASE NEW.payload->>'report_type'
          WHEN 'dre'        THEN 'dre_mensal'
          WHEN 'cash_flow'  THEN 'fluxo_caixa_diario'
          WHEN 'margin'     THEN 'relatorio_lucratividade'
          ELSE NULL
        END
      WHEN 'pesquisa_nps'            THEN 'pesquisa_nps'
      WHEN 'send_consumer_reply'     THEN NULL
      ELSE NULL
    END;
  END IF;

  IF v_doc_type_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (v_client_id, v_doc_type_id, 'complete', 'agent_generated', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'agent_generated',
          updated_at = now()
    WHERE client_knowledge_documents.status <> 'complete';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_completed] knowledge upsert failed for action_type=%, client=%: %',
      NEW.action_type, v_client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Tier guard in get_agent_readiness()
-- Agents with tier_required > client's current tier are 'blocked', regardless
-- of document coverage. Tier order: FREE < BASIC < PRO.
-- Also surfaces tier_blocked field so frontend can show the correct CTA.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_agent_readiness(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_result      jsonb;
  v_client_tier text;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read readiness for another client';
  END IF;

  -- Look up client tier; default to FREE if not found or NULL
  SELECT UPPER(COALESCE(tier, 'FREE'))
  INTO v_client_tier
  FROM public.clientes_blu
  WHERE client_id = p_client_id;

  v_client_tier := COALESCE(v_client_tier, 'FREE');

  WITH agent_doc_status AS (
    SELECT
      kar.agent_slug,
      kar.document_type_id,
      kar.requirement_type,
      kar.coverage_threshold,
      kdt.name            AS doc_name,
      kdt.coverage_weight,
      COALESCE(ckd.status, 'missing') AS client_doc_status,
      CASE COALESCE(ckd.status, 'missing')
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS status_score
    FROM public.knowledge_agent_requirements kar
    JOIN public.knowledge_document_types kdt
      ON  kdt.id = kar.document_type_id
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kar.document_type_id
      AND ckd.client_id        = p_client_id
  ),
  agent_scores AS (
    SELECT
      agent_slug,
      requirement_type,
      MAX(coverage_threshold) AS coverage_threshold,
      ROUND(
        SUM(status_score * coverage_weight) / NULLIF(SUM(coverage_weight), 0) * 100
      )::int AS weighted_pct,
      array_agg(doc_name ORDER BY doc_name)
        FILTER (WHERE requirement_type = 'minimum' AND client_doc_status = 'missing')
        AS missing_doc_names
    FROM agent_doc_status
    GROUP BY agent_slug, requirement_type
  ),
  agent_summary AS (
    SELECT
      s.agent_slug,
      cat.name          AS agent_name,
      cat.tier_required,
      (cea.enabled_at IS NOT NULL) AS is_enabled,
      MAX(CASE WHEN s.requirement_type = 'minimum'      THEN s.weighted_pct   ELSE 0   END) AS min_pct,
      MAX(CASE WHEN s.requirement_type = 'nice_to_have' THEN s.weighted_pct   ELSE 0   END) AS nice_pct,
      MAX(s.coverage_threshold) AS coverage_threshold,
      array_remove(
        array_agg(DISTINCT elem)
          FILTER (WHERE s.requirement_type = 'minimum'),
        NULL
      ) AS missing_names
    FROM agent_scores s
    CROSS JOIN LATERAL unnest(COALESCE(s.missing_doc_names, ARRAY[]::text[])) AS elem
    JOIN public.agent_catalog cat ON cat.slug = s.agent_slug
    LEFT JOIN public.client_enabled_agents cea
      ON cea.agent_slug = s.agent_slug AND cea.client_id = p_client_id
    GROUP BY s.agent_slug, cat.name, cat.tier_required, cea.enabled_at
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'agent_slug',       agent_slug,
      'agent_name',       agent_name,
      'tier_required',    tier_required,
      'is_enabled',       is_enabled,
      -- tier_blocked: client's subscription tier is below what this agent requires
      'tier_blocked',     CASE
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN true
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN true
                            ELSE false
                          END,
      'status',           CASE
                            -- Tier gate takes priority over document coverage
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN 'blocked'
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN 'blocked'
                            WHEN min_pct >= (coverage_threshold * 100)                                    THEN 'ready'
                            WHEN min_pct > 0                                                              THEN 'partial'
                            ELSE                                                                               'blocked'
                          END,
      'capability',       CASE WHEN nice_pct >= 70 THEN 'full' ELSE 'partial' END,
      'min_coverage_pct', min_pct,
      'nice_coverage_pct',nice_pct,
      'missing_docs',     COALESCE(to_jsonb(missing_names), '[]'::jsonb)
    ) ORDER BY agent_slug
  )
  INTO v_result
  FROM agent_summary;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;
