-- ── Phase 5: Cross-Agent Routine Executor ─────────────────────────────────────
-- Tracks routine executions and enqueues them when trigger conditions are met.
-- Dispatching = creating one approval_request per step; each approved step
-- then lands in client_knowledge_documents via the Phase 4 trigger.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Execution log table
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.client_routine_executions (
  id            uuid    DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id     uuid    NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  routine_id    text    NOT NULL REFERENCES public.cross_agent_routines(id),
  triggered_by  text    NOT NULL,  -- 'document_change' | 'cron' | 'manual'
  trigger_data  jsonb   NOT NULL DEFAULT '{}',
  status        text    NOT NULL DEFAULT 'pending',  -- pending | dispatched | completed | failed
  dispatched_at timestamp with time zone,
  created_at    timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_routine_exec_client   ON public.client_routine_executions (client_id, routine_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routine_exec_pending  ON public.client_routine_executions (status) WHERE status = 'pending';

ALTER TABLE public.client_routine_executions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own client" ON public.client_routine_executions
  FOR SELECT USING (client_id = public.get_my_client_id());

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Helper: enqueue a routine for a client (idempotent — one per cooldown window)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.enqueue_routine(
  p_client_id    uuid,
  p_routine_id   text,
  p_triggered_by text,
  p_trigger_data jsonb DEFAULT '{}'::jsonb,
  p_cooldown_h   integer DEFAULT 24   -- hours before same routine can re-fire
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id uuid;
BEGIN
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

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Trigger on client_knowledge_documents → enqueue document-based routines
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.on_knowledge_document_complete()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Only fire when status transitions to 'complete'
  IF OLD.status = NEW.status OR NEW.status <> 'complete' THEN
    RETURN NEW;
  END IF;

  BEGIN
    -- Enqueue every routine whose trigger_document_id matches this document type
    PERFORM public.enqueue_routine(
      NEW.client_id,
      car.id,
      'document_change',
      jsonb_build_object('document_type_id', NEW.document_type_id)
    )
    FROM public.cross_agent_routines car
    WHERE car.trigger_document_id = NEW.document_type_id;
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_knowledge_document_complete] enqueue failed for doc=%, client=%: %',
      NEW.document_type_id, NEW.client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enqueue_routine_on_doc_complete ON public.client_knowledge_documents;
CREATE TRIGGER trg_enqueue_routine_on_doc_complete
  AFTER UPDATE OF status ON public.client_knowledge_documents
  FOR EACH ROW
  EXECUTE FUNCTION public.on_knowledge_document_complete();

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Dispatcher: for each pending execution, create one approval request per step
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.process_pending_routine_executions()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_exec    record;
  v_routine record;
  v_step    jsonb;
  v_done    integer := 0;
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
        INSERT INTO public.approval_requests
          (client_id, action_type, agent_slug, payload, expires_at)
        VALUES (
          v_exec.client_id,
          v_step->>'action',
          v_step->>'agent',
          jsonb_build_object(
            'routine_id',       v_exec.routine_id,
            'execution_id',     v_exec.id,
            'step',             (v_step->>'step')::integer,
            'expected_output',  v_step->>'output',
            'routine_name',     v_routine.name
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

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Monthly close enqueue: fires for all onboarded clients on the last day
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.enqueue_monthly_close()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_last_day date;
  v_today    date := current_date;
  v_enqueued integer := 0;
  v_client_id uuid;
BEGIN
  -- Calculate last day of current month
  v_last_day := (date_trunc('month', now()) + interval '1 month' - interval '1 day')::date;

  IF v_today <> v_last_day THEN
    RETURN 0;  -- not last day of month
  END IF;

  FOR v_client_id IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    IF public.enqueue_routine(
      v_client_id,
      'monthly_close',
      'cron',
      jsonb_build_object('month', to_char(now(), 'YYYY-MM')),
      -- Cooldown 600 hours (~25 days) so it can't fire twice in one month
      600
    ) IS NOT NULL THEN
      v_enqueued := v_enqueued + 1;
    END IF;
  END LOOP;

  RETURN v_enqueued;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. pg_cron jobs
-- ─────────────────────────────────────────────────────────────────────────────

-- Process pending executions every minute (alongside existing ETL job)
SELECT cron.schedule(
  'process_pending_routine_executions',
  '* * * * *',
  $$ SELECT public.process_pending_routine_executions(); $$
);

-- Enqueue monthly_close check — runs at 23:00 on days 28–31; function guards last-day
SELECT cron.schedule(
  'enqueue_monthly_close',
  '0 23 28-31 * *',
  $$ SELECT public.enqueue_monthly_close(); $$
);
