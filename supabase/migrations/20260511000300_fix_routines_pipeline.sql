-- ─────────────────────────────────────────────────────────────────────────────
-- Fix routines pipeline so executions actually generate tasks on the mesa de
-- trabalho.
--
-- Bugs fixed:
--   1. approval_requests had no `body` column — DecisionCard always showed blank
--   2. process_pending_routine_executions() never set title/body on inserts
--   3. enqueue_routine() didn't respect client_routines.active = false
--   4. project_wrap had trigger_document_id = NULL — could never be enqueued
--      via the document trigger (NULL = anything is always false in SQL)
--   5. 4 document types referenced as step outputs were missing from
--      knowledge_document_types, causing FK violations that silently failed
--      every routine execution
--   6. Add enqueue_routine_for_me() so the admin UI can manually test routines
-- ─────────────────────────────────────────────────────────────────────────────


-- 1. Add missing document types referenced as step outputs in cross_agent_routines.
--    Without these, process_pending_routine_executions() throws a FK violation
--    when pre-marking outputs as 'partial', rolls back all approval_request
--    INSERTs, and marks the execution as 'failed'.
INSERT INTO public.knowledge_document_types (id, domain_id, name, type) VALUES
  ('cronograma_evento',   'operacoes',  'Cronograma de Evento',     'schedule'),
  ('evento',              'operacoes',  'Evento / Compromisso',      'schedule'),
  ('portfolio_update',    'estrategia', 'Atualização de Portfólio',  'strategy'),
  ('testimonial_request', 'externo',    'Solicitação de Depoimento', 'crm')
ON CONFLICT (id) DO NOTHING;


-- 2. Add body column to approval_requests (DecisionCard reads it)
ALTER TABLE public.approval_requests
  ADD COLUMN IF NOT EXISTS body text;


-- 3. Fix project_wrap: give it a real trigger_document_id so the
--    on_knowledge_document_complete trigger can match it.
--    cronograma_evento is the natural trigger: when the event timeline document
--    is finalised (status → 'complete') the wrap-up steps begin.
UPDATE public.cross_agent_routines
  SET trigger_document_id = 'cronograma_evento'
WHERE id = 'project_wrap'
  AND trigger_document_id IS NULL;


-- 4. Fix enqueue_routine() — respect client_routines.active = false
CREATE OR REPLACE FUNCTION public.enqueue_routine(
  p_client_id    uuid,
  p_routine_id   text,
  p_triggered_by text,
  p_trigger_data jsonb  DEFAULT '{}'::jsonb,
  p_cooldown_h   integer DEFAULT 24
) RETURNS uuid
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_id uuid;
BEGIN
  -- Respect per-client opt-out
  IF EXISTS (
    SELECT 1 FROM public.client_routines
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND active     = false
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


-- 5. Fix process_pending_routine_executions() — set title and body on each
--    approval_request so DecisionCards render meaningful content.
CREATE OR REPLACE FUNCTION public.process_pending_routine_executions()
  RETURNS integer
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = 'public'
AS $$
DECLARE
  v_exec    record;
  v_routine record;
  v_step    jsonb;
  v_done    integer := 0;
  v_step_n  integer;
  v_action  text;
  v_title   text;
  v_body    text;
BEGIN
  FOR v_exec IN
    SELECT cre.*
    FROM public.client_routine_executions cre
    WHERE cre.status = 'pending'
    ORDER BY cre.created_at
    LIMIT 20
  LOOP
    SELECT * INTO v_routine
    FROM public.cross_agent_routines
    WHERE id = v_exec.routine_id;

    IF NOT FOUND THEN
      UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
      CONTINUE;
    END IF;

    BEGIN
      -- Create one approval_request per step
      FOR v_step IN SELECT value FROM jsonb_array_elements(v_routine.steps)
      LOOP
        v_step_n := (v_step->>'step')::integer;
        v_action := replace(v_step->>'action', '_', ' ');
        v_title  := v_routine.name || ' · Passo ' || v_step_n || ': ' || v_action;
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
            'routine_name',    v_routine.name
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


-- 6. Helper so the admin UI can manually enqueue any routine for the current
--    client without exposing the raw enqueue_routine(uuid, …) signature.
CREATE OR REPLACE FUNCTION public.enqueue_routine_for_me(p_routine_id text)
  RETURNS uuid
  LANGUAGE sql SECURITY DEFINER
  SET search_path = 'public'
AS $$
  SELECT public.enqueue_routine(
    public.get_my_client_id(),
    p_routine_id,
    'manual',
    jsonb_build_object('triggered_from', 'admin_ui'),
    0   -- no cooldown for manual triggers
  );
$$;

GRANT EXECUTE ON FUNCTION public.enqueue_routine_for_me(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.enqueue_routine_for_me(text) TO service_role;
