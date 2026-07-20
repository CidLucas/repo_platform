-- ── Phase 4: Agent-Generated Document Tracking ────────────────────────────────
-- Adds agent_slug to approval_requests, fixes request_approval RPC signature to
-- match what the framework sends, and tracks approved actions as knowledge documents.

-- 1. Add agent_slug column
ALTER TABLE public.approval_requests
  ADD COLUMN IF NOT EXISTS agent_slug text;

CREATE INDEX IF NOT EXISTS idx_approval_agent_slug
  ON public.approval_requests (client_id, agent_slug);

-- 2. Drop old overload (3-arg version) before replacing to avoid PostgREST ambiguity
DROP FUNCTION IF EXISTS public.request_approval(text, jsonb, timestamp with time zone);

-- 2b. Replace request_approval to accept full framework parameter set
--    Old signature: (p_action_type, p_payload, p_expires_at)
--    Framework sends: (p_agent_slug, p_action, p_payload, p_session_id,
--                      p_tool_call_id, p_routed_to_role, p_sla_hours)
--    We accept all forms via defaults so existing callers keep working.
CREATE OR REPLACE FUNCTION public.request_approval(
  -- Original params (keep for back-compat)
  p_action_type     text                     DEFAULT NULL,
  p_payload         jsonb                    DEFAULT '{}'::jsonb,
  p_expires_at      timestamp with time zone DEFAULT NULL,
  -- Framework params
  p_agent_slug      text                     DEFAULT NULL,
  p_action          text                     DEFAULT NULL,   -- alias for p_action_type
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
    (client_id, requested_by, action_type, agent_slug, payload, expires_at)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, v_action_type, p_agent_slug, p_payload, v_expires_at)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

-- 3. Trigger function: map approved actions → client_knowledge_documents
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
  -- Only fire when transitioning to 'approved'
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  IF v_client_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Map action_type → document_type_id
  v_doc_type_id := CASE NEW.action_type
    -- compras: RFQ / purchase orders
    WHEN 'create_purchase_order'   THEN 'cotacao_rfq'
    WHEN 'approve_purchase_order'  THEN 'ordem_compra'
    -- documentos: commercial proposals
    WHEN 'comercial.draft_created' THEN 'proposta_comercial'
    -- financeiro: reports — disambiguate by payload
    WHEN 'reports.generate'        THEN
      CASE NEW.payload->>'report_type'
        WHEN 'dre'        THEN 'dre_mensal'
        WHEN 'cash_flow'  THEN 'fluxo_caixa_diario'
        WHEN 'margin'     THEN 'relatorio_lucratividade'
        ELSE NULL   -- unknown report type, skip
      END
    -- estrategia: NPS surveys
    WHEN 'pesquisa_nps'            THEN 'pesquisa_nps'
    -- skip operational actions that aren't knowledge documents
    WHEN 'send_consumer_reply'     THEN NULL
    ELSE NULL
  END;

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
    -- Never downgrade: only overwrite if not already 'complete'
    WHERE client_knowledge_documents.status <> 'complete';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_completed] knowledge upsert failed for action_type=%, client=%: %',
      NEW.action_type, v_client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_knowledge_on_approval_completed ON public.approval_requests;
CREATE TRIGGER trg_knowledge_on_approval_completed
  AFTER UPDATE OF status ON public.approval_requests
  FOR EACH ROW
  EXECUTE FUNCTION public.on_approval_completed();
