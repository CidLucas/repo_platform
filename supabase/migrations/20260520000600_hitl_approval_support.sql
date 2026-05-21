-- ─────────────────────────────────────────────────────────────────────────────
-- HITL (Human-in-the-Loop) approval support for routine executions
--
-- 1. Extends client_routine_executions.status with 'awaiting_approval'
-- 2. Adds redispatch_routine_after_approval() trigger function:
--    When an approval_request with action_type='routine_hitl' transitions to
--    'approved', the linked execution is re-dispatched by setting its status
--    back to 'dispatched' so the cron poller picks it up and resumes from the
--    saved _resume_from_step checkpoint in result_metadata.
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. Extend status constraint ──────────────────────────────────────────────

ALTER TABLE public.client_routine_executions
  DROP CONSTRAINT IF EXISTS client_routine_executions_status_check;

ALTER TABLE public.client_routine_executions
  ADD CONSTRAINT client_routine_executions_status_check
  CHECK (status IN ('pending', 'dispatched', 'executing', 'completed', 'failed', 'awaiting_approval'));

-- Partial index for the HITL queue (so the dashboard can surface paused executions)
CREATE INDEX IF NOT EXISTS idx_routine_exec_awaiting_approval
  ON public.client_routine_executions (client_id, dispatched_at)
  WHERE status = 'awaiting_approval';


-- ── 2. Re-dispatch trigger ───────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.redispatch_routine_after_approval()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_exec_id TEXT;
BEGIN
  -- Only act when a routine_hitl approval transitions to 'approved'
  IF NEW.action_type <> 'routine_hitl'
     OR NEW.status <> 'approved'
     OR OLD.status = 'approved'
  THEN
    RETURN NEW;
  END IF;

  v_exec_id := NEW.payload ->> 'execution_id';
  IF v_exec_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Re-dispatch only if the execution is still waiting for this approval
  UPDATE public.client_routine_executions
    SET status        = 'dispatched',
        dispatched_at = NOW()
  WHERE id::TEXT     = v_exec_id
    AND status        = 'awaiting_approval';

  RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.redispatch_routine_after_approval() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.redispatch_routine_after_approval() FROM anon, authenticated;

-- Drop and recreate to avoid duplicate trigger
DROP TRIGGER IF EXISTS trg_redispatch_after_approval ON public.approval_requests;

CREATE TRIGGER trg_redispatch_after_approval
  AFTER UPDATE OF status ON public.approval_requests
  FOR EACH ROW
  EXECUTE FUNCTION public.redispatch_routine_after_approval();
