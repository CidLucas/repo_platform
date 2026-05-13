-- ─────────────────────────────────────────────────────────────────────────────
-- Routine Execution Bridge
--
-- 1. Drop FK that blocks custom (UUID) routine_ids from being stored
-- 2. Add result columns + 'executing'/'completed' statuses
-- 3. Add claim_routine_executions() for atomic batch claiming (SKIP LOCKED)
-- 4. Schedule pg_cron → pg_net to call atendente_core every minute
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. Drop FK blocking custom routine UUIDs ─────────────────────────────────

ALTER TABLE public.client_routine_executions
  DROP CONSTRAINT IF EXISTS client_routine_executions_routine_id_fkey;


-- ── 2. Result columns + extended status constraint ───────────────────────────

ALTER TABLE public.client_routine_executions
  ADD COLUMN IF NOT EXISTS result_text     text,
  ADD COLUMN IF NOT EXISTS result_metadata jsonb        DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS completed_at    timestamptz,
  ADD COLUMN IF NOT EXISTS worker_slug     text;

-- Widen status to include 'executing' and 'completed'
ALTER TABLE public.client_routine_executions
  DROP CONSTRAINT IF EXISTS client_routine_executions_status_check;

ALTER TABLE public.client_routine_executions
  ADD CONSTRAINT client_routine_executions_status_check
  CHECK (status IN ('pending', 'dispatched', 'executing', 'completed', 'failed'));

-- Index for the new dispatcher (queries WHERE status = 'dispatched')
CREATE INDEX IF NOT EXISTS idx_routine_exec_dispatched
  ON public.client_routine_executions (dispatched_at)
  WHERE status = 'dispatched';


-- ── 3. Atomic batch claim function ───────────────────────────────────────────
--
-- Uses FOR UPDATE SKIP LOCKED so two concurrent cron ticks never claim the
-- same row.  Returns the full rows so Python doesn't need a second SELECT.

CREATE OR REPLACE FUNCTION public.claim_routine_executions(
  p_batch_size integer DEFAULT 10
)
RETURNS SETOF public.client_routine_executions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  UPDATE public.client_routine_executions
    SET status = 'executing'
  WHERE id IN (
    SELECT id
    FROM   public.client_routine_executions
    WHERE  status = 'dispatched'
    ORDER  BY dispatched_at
    LIMIT  p_batch_size
    FOR    UPDATE SKIP LOCKED
  )
  RETURNING *;
END;
$$;

-- Only callable by postgres / service_role — never by anon or authenticated JWT users
REVOKE EXECUTE ON FUNCTION public.claim_routine_executions(integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.claim_routine_executions(integer) FROM anon, authenticated;


-- ── 4. pg_cron → pg_net: call atendente_core every minute ───────────────────
--
-- Requires:
--   ALTER DATABASE postgres SET app.atendente_core_url  = 'https://...';
--   ALTER DATABASE postgres SET app.routine_dispatch_token = 'secret';
--
-- The HTTP call returns 202 immediately (background task pattern); pg_net's
-- 30 s default timeout is not a problem.

CREATE OR REPLACE FUNCTION public.dispatch_routine_executions()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  _url   text := current_setting('app.atendente_core_url',    true);
  _token text := current_setting('app.routine_dispatch_token', true);
BEGIN
  IF _url IS NULL OR _token IS NULL THEN
    RAISE WARNING '[dispatch_routine_executions] app settings not configured — skipping';
    RETURN;
  END IF;

  PERFORM extensions.http_post(
    url     := _url || '/internal/routines/run-dispatched',
    headers := jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', 'Bearer ' || _token
    ),
    body    := '{}'
  );
END;
$$;

-- Only callable by postgres / service_role — prevents any JWT user from
-- triggering authenticated HTTP calls to the backend.
REVOKE EXECUTE ON FUNCTION public.dispatch_routine_executions() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.dispatch_routine_executions() FROM anon, authenticated;

SELECT cron.schedule(
  'dispatch_routine_executions_to_agent',
  '* * * * *',
  $$ SELECT public.dispatch_routine_executions(); $$
);
