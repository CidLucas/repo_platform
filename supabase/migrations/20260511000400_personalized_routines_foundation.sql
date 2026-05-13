-- ─────────────────────────────────────────────────────────────────────────────
-- Personalized Routines Foundation
--
-- Allows clients to create custom routines via guided builder or AI chat.
--
-- Changes:
--   1. agent_action_catalog — catalog of what each agent can do
--   2. Extend client_routines — support custom (non-catalog) routines with
--      inline steps, source tracking, approval-gated activation
--   3. cross_agent_routines.config_schema — expose configurable params per routine
--   4. enqueue_routine() — respect status = 'active' for custom routines
--   5. process_pending_routine_executions() — resolve steps from both
--      cross_agent_routines (catalog) and client_routines.steps (custom)
--   6. on_approval_completed() — handle routine_activation action type +
--      dynamic catalog lookup for agent action outputs
-- ─────────────────────────────────────────────────────────────────────────────


-- ─── 1. agent_action_catalog ─────────────────────────────────────────────────
-- Catalog of discrete actions each agent can perform, referenced when building
-- custom routine steps. Seeded externally by the user/admin.

CREATE TABLE IF NOT EXISTS public.agent_action_catalog (
  id                  text        PRIMARY KEY,   -- '<agent_slug>.<action_id>'
  agent_slug          text        NOT NULL,
  action_id           text        NOT NULL,
  label               text        NOT NULL,
  description         text,
  input_schema        jsonb       NOT NULL DEFAULT '[]'::jsonb,  -- [{name, type, label, required}]
  output_doc_type_id  text        REFERENCES public.knowledge_document_types(id) ON DELETE SET NULL,
  trigger_capable     boolean     NOT NULL DEFAULT false,
  is_active           boolean     NOT NULL DEFAULT true,
  sort_order          integer     NOT NULL DEFAULT 0,
  UNIQUE (agent_slug, action_id)
);

ALTER TABLE public.agent_action_catalog OWNER TO postgres;

-- RLS: agents can read their own catalog entries; admin can write
ALTER TABLE public.agent_action_catalog ENABLE ROW LEVEL SECURITY;

CREATE POLICY "authenticated can read active catalog"
  ON public.agent_action_catalog FOR SELECT
  TO authenticated
  USING (is_active = true);

CREATE POLICY "service_role full access to catalog"
  ON public.agent_action_catalog FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

COMMENT ON TABLE public.agent_action_catalog IS
  'Catalog of actions each Blu agent can perform. Used as building blocks for custom client routines.';


-- ─── 2. Extend client_routines ───────────────────────────────────────────────

-- source: 'catalog' = reference to cross_agent_routines; 'custom' = user-defined inline steps
ALTER TABLE public.client_routines
  ADD COLUMN IF NOT EXISTS source       text NOT NULL DEFAULT 'catalog'
    CHECK (source IN ('catalog', 'custom')),
  ADD COLUMN IF NOT EXISTS status       text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'pending_approval', 'draft')),
  ADD COLUMN IF NOT EXISTS name         text,
  ADD COLUMN IF NOT EXISTS description  text,
  ADD COLUMN IF NOT EXISTS steps        jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS trigger_type text DEFAULT 'manual'
    CHECK (trigger_type IN ('manual', 'document', 'schedule', 'event')),
  ADD COLUMN IF NOT EXISTS trigger_config jsonb DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS created_by_ai boolean NOT NULL DEFAULT false;

-- Index to quickly find custom routines pending execution
CREATE INDEX IF NOT EXISTS idx_client_routines_source_status
  ON public.client_routines (source, status);


-- ─── 3. cross_agent_routines: expose configurable params ────────────────────

ALTER TABLE public.cross_agent_routines
  ADD COLUMN IF NOT EXISTS config_schema jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.cross_agent_routines.config_schema IS
  'Array of {key, label, type, default, required} describing params the client can configure for this routine.';


-- ─── 4. enqueue_routine() — also support custom client_routines by UUID ─────
-- Overloaded approach: keep the (client_id, routine_id text) signature for
-- catalog routines; add a new function for custom routines by their UUID.

CREATE OR REPLACE FUNCTION public.enqueue_routine(
  p_client_id    uuid,
  p_routine_id   text,
  p_triggered_by text,
  p_trigger_data jsonb   DEFAULT '{}'::jsonb,
  p_cooldown_h   integer DEFAULT 24
) RETURNS uuid
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_id uuid;
BEGIN
  -- Respect per-client opt-out (active = false OR status != 'active')
  IF EXISTS (
    SELECT 1 FROM public.client_routines
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND (active = false OR status <> 'active')
  ) THEN
    RETURN NULL;
  END IF;

  -- Skip if same routine fired within cooldown window
  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (p_client_id, p_routine_id, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


-- Enqueue a custom client_routine by its UUID (not the cross_agent_routines text id)
CREATE OR REPLACE FUNCTION public.enqueue_custom_routine(
  p_client_routine_id  uuid,
  p_triggered_by       text,
  p_trigger_data       jsonb   DEFAULT '{}'::jsonb,
  p_cooldown_h         integer DEFAULT 24
) RETURNS uuid
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_cr      record;
  v_exec_id uuid;
BEGIN
  SELECT * INTO v_cr
  FROM public.client_routines
  WHERE id = p_client_routine_id;

  IF NOT FOUND THEN RETURN NULL; END IF;

  -- Must be active
  IF v_cr.active = false OR v_cr.status <> 'active' THEN
    RETURN NULL;
  END IF;

  -- Cooldown: use routine UUID as the execution key
  IF p_cooldown_h > 0 AND EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = v_cr.client_id
      AND routine_id = v_cr.id::text
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (v_cr.client_id, v_cr.id::text, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_exec_id;

  RETURN v_exec_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.enqueue_custom_routine(uuid, text, jsonb, integer)
  TO authenticated, service_role;


-- ─── 5. process_pending_routine_executions() — dual-source step resolution ──
CREATE OR REPLACE FUNCTION public.process_pending_routine_executions()
  RETURNS integer
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_exec       record;
  v_routine    record;      -- cross_agent_routines row (catalog)
  v_cr         record;      -- client_routines row (custom)
  v_steps      jsonb;
  v_step       jsonb;
  v_done       integer := 0;
  v_step_n     integer;
  v_action     text;
  v_title      text;
  v_body       text;
  v_routine_name text;
  v_is_custom  boolean;
BEGIN
  FOR v_exec IN
    SELECT cre.*
    FROM public.client_routine_executions cre
    WHERE cre.status = 'pending'
    ORDER BY cre.created_at
    LIMIT 20
  LOOP
    -- Determine source: try UUID parse first (custom routines store UUID as text)
    v_is_custom := (v_exec.routine_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

    IF v_is_custom THEN
      SELECT * INTO v_cr
      FROM public.client_routines
      WHERE id = v_exec.routine_id::uuid
        AND client_id = v_exec.client_id
        AND source = 'custom';

      IF NOT FOUND THEN
        UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
        CONTINUE;
      END IF;

      v_steps        := v_cr.steps;
      v_routine_name := COALESCE(v_cr.name, 'Rotina Personalizada');
    ELSE
      SELECT * INTO v_routine
      FROM public.cross_agent_routines
      WHERE id = v_exec.routine_id;

      IF NOT FOUND THEN
        UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
        CONTINUE;
      END IF;

      v_steps        := v_routine.steps;
      v_routine_name := v_routine.name;
    END IF;

    BEGIN
      FOR v_step IN SELECT value FROM jsonb_array_elements(v_steps)
      LOOP
        v_step_n := (v_step->>'step')::integer;
        v_action := replace(v_step->>'action', '_', ' ');
        v_title  := v_routine_name || ' · Passo ' || v_step_n || ': ' || v_action;
        v_body   := 'O agente ' || (v_step->>'agent') || ' precisa da sua aprovação para: ' || v_action || '.';

        INSERT INTO public.approval_requests
          (client_id, action_type, agent_slug, title, body, payload, expires_at)
        VALUES (
          v_exec.client_id,
          v_step->>'action',
          v_step->>'agent',
          v_title,
          v_body,
          jsonb_build_object(
            'routine_id',      v_exec.routine_id,
            'execution_id',    v_exec.id,
            'step',            v_step_n,
            'expected_output', v_step->>'output',
            'routine_name',    v_routine_name,
            'is_custom',       v_is_custom
          ),
          now() + interval '7 days'
        );

        -- Pre-mark output document as partial (in-progress)
        IF v_step->>'output' IS NOT NULL THEN
          INSERT INTO public.client_knowledge_documents
            (client_id, document_type_id, status, source, updated_at)
          VALUES
            (v_exec.client_id, v_step->>'output', 'partial', 'agent_generated', now())
          ON CONFLICT (client_id, document_type_id) DO UPDATE
            SET status     = 'partial',
                updated_at = now()
          WHERE client_knowledge_documents.status = 'missing';
        END IF;
      END LOOP;

      UPDATE public.client_routine_executions
        SET status = 'dispatched', dispatched_at = now()
      WHERE id = v_exec.id;

      v_done := v_done + 1;

    EXCEPTION WHEN others THEN
      UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
      RAISE WARNING '[process_pending_routine_executions] failed for execution %: %', v_exec.id, SQLERRM;
    END;
  END LOOP;

  RETURN v_done;
END;
$$;


-- ─── 6. on_approval_completed() — routine_activation + dynamic catalog ───────
CREATE OR REPLACE FUNCTION public.on_approval_completed()
  RETURNS trigger
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_doc_type_id  text;
  v_client_id    uuid := NEW.client_id;
  v_cr_id        uuid;
BEGIN
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  IF v_client_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- ── Special: routine_activation — activate a draft/pending_approval custom routine
  IF NEW.action_type = 'routine_activation' THEN
    BEGIN
      v_cr_id := (NEW.payload->>'client_routine_id')::uuid;
      IF v_cr_id IS NOT NULL THEN
        UPDATE public.client_routines
          SET status = 'active', active = true
        WHERE id = v_cr_id
          AND client_id = v_client_id;
      END IF;
    EXCEPTION WHEN others THEN
      RAISE WARNING '[on_approval_completed] routine_activation failed for client=%: %', v_client_id, SQLERRM;
    END;
    RETURN NEW;
  END IF;

  -- ── Routine-dispatched action: use expected_output from payload
  IF NEW.payload->>'routine_id' IS NOT NULL THEN
    v_doc_type_id := NEW.payload->>'expected_output';

  -- ── Dynamic catalog lookup: check agent_action_catalog first
  ELSIF EXISTS (
    SELECT 1 FROM public.agent_action_catalog
    WHERE id = NEW.action_type AND is_active = true
  ) THEN
    SELECT output_doc_type_id INTO v_doc_type_id
    FROM public.agent_action_catalog
    WHERE id = NEW.action_type;

  -- ── Legacy static map for direct agent actions
  ELSE
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


-- ─── 7. enqueue_routine_for_me — updated to also handle custom routine UUIDs ─
CREATE OR REPLACE FUNCTION public.enqueue_routine_for_me(p_routine_id text)
  RETURNS uuid
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_is_uuid   boolean;
BEGIN
  v_is_uuid := (p_routine_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

  IF v_is_uuid THEN
    RETURN public.enqueue_custom_routine(
      p_routine_id::uuid,
      'manual',
      jsonb_build_object('triggered_from', 'admin_ui'),
      0
    );
  ELSE
    RETURN public.enqueue_routine(
      v_client_id,
      p_routine_id,
      'manual',
      jsonb_build_object('triggered_from', 'admin_ui'),
      0
    );
  END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION public.enqueue_routine_for_me(text)  TO authenticated, service_role;
