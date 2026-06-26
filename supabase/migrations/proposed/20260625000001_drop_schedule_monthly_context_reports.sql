-- 20260625000001_drop_schedule_monthly_context_reports.sql
-- Phase 4.1 (M7) of the edge-functions rationalization plan.
--
-- ``public.schedule_monthly_context_reports()`` is an orphan. It is
-- defined in 20260523999999_baseline_v2.sql and meant to be called by a
-- pg_cron job that fires monthly, but no ``cron.schedule(...)`` call
-- references it (verified by grep across the whole migrations tree).
-- The comment in the Deno ``generate-context-report`` EF that said
-- "monthly via pg_cron" was aspirational, not real.
--
-- With the Deno EF gone (commit TBD), the only remaining caller
-- (onboarding-bootstrap) now talks to agent_api's
-- ``/v1/internal/context-report`` endpoint instead. There is no
-- remaining path that needs this function. DROP it.
--
-- Idempotency: ``DROP FUNCTION IF EXISTS`` so re-runs are safe.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

DROP FUNCTION IF EXISTS public.schedule_monthly_context_reports();

COMMIT;
