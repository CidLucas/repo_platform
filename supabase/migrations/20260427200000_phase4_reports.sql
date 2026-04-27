-- Migration: Phase 4 — Reports & Document Generation foundation.
--
-- Creates persistence for report runs (every time the report_module
-- composes a deliverable) and scheduled reports (PRO+ feature where the
-- system regenerates a template on a fixed cadence).
--
-- Tables:
--   public.report_runs        one row per generated report
--   public.report_schedules   one row per (client_id, template_id, cadence)
--
-- RPCs:
--   list_report_runs(p_limit int default 50)
--   list_report_schedules()
--   schedule_due_reports() -- helper used by cron worker (returns due rows)
--
-- Tickets: BLU-MVP-060, BLU-MVP-063.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. report_runs
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.report_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    template_id     TEXT NOT NULL,
    period          TEXT NOT NULL DEFAULT '30d',
    format          TEXT NOT NULL CHECK (format IN ('markdown', 'pdf', 'xlsx', 'gdoc', 'gsheet')),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'running', 'success', 'failed')),
    -- For markdown/pdf/xlsx the body is stored inline as base64 in
    -- output_metadata.payload_b64; for gdoc/gsheet output_url points at the
    -- created Google resource.
    output_url      TEXT,
    output_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    requested_by    UUID,                                   -- auth.uid() (nullable for cron)
    schedule_id     UUID,                                   -- FK set below
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_runs_client_created
    ON public.report_runs(client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_runs_template
    ON public.report_runs(client_id, template_id, created_at DESC);

ALTER TABLE public.report_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS report_runs_select_own ON public.report_runs;
CREATE POLICY report_runs_select_own
    ON public.report_runs FOR SELECT
    USING (client_id = public.get_my_client_id()::uuid);

DROP POLICY IF EXISTS report_runs_service ON public.report_runs;
CREATE POLICY report_runs_service
    ON public.report_runs FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Direct INSERT/UPDATE from the dashboard JWT is forbidden — all writes go
-- through the tool_pool_api service-role path so we can validate template
-- IDs and audit the action.
DROP POLICY IF EXISTS report_runs_insert_authenticated ON public.report_runs;
CREATE POLICY report_runs_insert_authenticated
    ON public.report_runs FOR INSERT TO authenticated
    WITH CHECK (false);

-- ─────────────────────────────────────────────────────────────────────
-- 2. report_schedules
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.report_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    template_id     TEXT NOT NULL,
    period          TEXT NOT NULL DEFAULT '30d',
    format          TEXT NOT NULL DEFAULT 'pdf'
                    CHECK (format IN ('markdown', 'pdf', 'xlsx', 'gdoc', 'gsheet')),
    cadence         TEXT NOT NULL DEFAULT 'monthly'
                    CHECK (cadence IN ('daily', 'weekly', 'monthly')),
    enabled         BOOLEAN NOT NULL DEFAULT true,
    notify_channel  TEXT NOT NULL DEFAULT 'app'
                    CHECK (notify_channel IN ('app', 'email', 'whatsapp')),
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    config          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, template_id, cadence)
);

CREATE INDEX IF NOT EXISTS idx_report_schedules_due
    ON public.report_schedules(next_run_at) WHERE enabled;
CREATE INDEX IF NOT EXISTS idx_report_schedules_client
    ON public.report_schedules(client_id);

ALTER TABLE public.report_schedules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS report_schedules_select_own ON public.report_schedules;
CREATE POLICY report_schedules_select_own
    ON public.report_schedules FOR SELECT
    USING (client_id = public.get_my_client_id()::uuid);

DROP POLICY IF EXISTS report_schedules_service ON public.report_schedules;
CREATE POLICY report_schedules_service
    ON public.report_schedules FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Wire the FK now that report_schedules exists.
ALTER TABLE public.report_runs
    DROP CONSTRAINT IF EXISTS report_runs_schedule_id_fkey;
ALTER TABLE public.report_runs
    ADD CONSTRAINT report_runs_schedule_id_fkey
    FOREIGN KEY (schedule_id)
    REFERENCES public.report_schedules(id) ON DELETE SET NULL;

-- updated_at touch trigger.
CREATE OR REPLACE FUNCTION public.tg_report_schedules_touch()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS report_schedules_touch ON public.report_schedules;
CREATE TRIGGER report_schedules_touch
    BEFORE UPDATE ON public.report_schedules
    FOR EACH ROW EXECUTE FUNCTION public.tg_report_schedules_touch();

-- ─────────────────────────────────────────────────────────────────────
-- 3. RPCs
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.list_report_runs(
    p_limit int DEFAULT 50
)
RETURNS TABLE (
    id              uuid,
    template_id     text,
    period          text,
    format          text,
    status          text,
    output_url      text,
    output_metadata jsonb,
    error_message   text,
    schedule_id     uuid,
    started_at      timestamptz,
    finished_at     timestamptz,
    created_at      timestamptz
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    SELECT id, template_id, period, format, status, output_url,
           output_metadata, error_message, schedule_id,
           started_at, finished_at, created_at
      FROM public.report_runs
     WHERE client_id = public.get_my_client_id()::uuid
     ORDER BY created_at DESC
     LIMIT GREATEST(1, LEAST(p_limit, 200));
$$;

GRANT EXECUTE ON FUNCTION public.list_report_runs(int) TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.list_report_schedules()
RETURNS TABLE (
    id              uuid,
    template_id     text,
    period          text,
    format          text,
    cadence         text,
    enabled         boolean,
    notify_channel  text,
    last_run_at     timestamptz,
    next_run_at     timestamptz,
    config          jsonb,
    created_at      timestamptz,
    updated_at      timestamptz
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    SELECT id, template_id, period, format, cadence, enabled, notify_channel,
           last_run_at, next_run_at, config, created_at, updated_at
      FROM public.report_schedules
     WHERE client_id = public.get_my_client_id()::uuid
     ORDER BY next_run_at ASC;
$$;

GRANT EXECUTE ON FUNCTION public.list_report_schedules() TO authenticated, service_role;

-- Helper used by the cron-triggered worker. Service-role only; bypasses RLS
-- by design to enumerate due schedules across tenants.
CREATE OR REPLACE FUNCTION public.list_due_report_schedules(
    p_limit int DEFAULT 50
)
RETURNS TABLE (
    id              uuid,
    client_id       uuid,
    template_id     text,
    period          text,
    format          text,
    cadence         text,
    notify_channel  text,
    config          jsonb
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT id, client_id, template_id, period, format, cadence,
           notify_channel, config
      FROM public.report_schedules
     WHERE enabled = true
       AND next_run_at <= now()
     ORDER BY next_run_at ASC
     LIMIT GREATEST(1, LEAST(p_limit, 200));
$$;

REVOKE ALL ON FUNCTION public.list_due_report_schedules(int) FROM PUBLIC, authenticated;
GRANT EXECUTE ON FUNCTION public.list_due_report_schedules(int) TO service_role;

-- ─────────────────────────────────────────────────────────────────────
-- 4. Service-role indicator dispatcher
-- ─────────────────────────────────────────────────────────────────────
-- The dimension indicator RPCs in `analytics_v2` use SECURITY INVOKER and
-- read `public.get_my_client_id()` (which inspects the JWT's `email`
-- claim). The report module needs to call them from a service-role
-- context — both for the interactive UX and for the scheduled cron — so
-- this dispatcher synthesizes the JWT claims block, runs the indicator
-- query, and returns the single row as JSON.

CREATE OR REPLACE FUNCTION analytics_v2.get_indicator_block_for(
    p_client_id   uuid,
    p_template_id text,
    p_period      text DEFAULT '30d'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public, pg_temp
AS $$
DECLARE
    v_email   text;
    v_result  jsonb;
BEGIN
    SELECT email INTO v_email
      FROM public.clientes_vizu
     WHERE client_id = p_client_id
     LIMIT 1;

    IF v_email IS NULL THEN
        RAISE EXCEPTION 'get_indicator_block_for: client_id % has no clientes_vizu row', p_client_id;
    END IF;

    -- Inject the synthetic JWT context the indicator RPCs expect.
    PERFORM set_config(
        'request.jwt.claims',
        json_build_object('email', v_email)::text,
        true
    );

    CASE p_template_id
        WHEN 'mensal_comercial' THEN
            SELECT to_jsonb(t) INTO v_result
              FROM analytics_v2.get_commercial_indicators(p_period) t;
        WHEN 'estoque_critico' THEN
            SELECT to_jsonb(t) INTO v_result
              FROM analytics_v2.get_inventory_indicators(p_period) t;
        WHEN 'cotacoes_do_mes' THEN
            SELECT to_jsonb(t) INTO v_result
              FROM analytics_v2.get_supply_indicators(p_period) t;
        WHEN 'caixa_semanal' THEN
            SELECT to_jsonb(t) INTO v_result
              FROM analytics_v2.get_finance_indicators(p_period) t;
        ELSE
            RAISE EXCEPTION 'get_indicator_block_for: unknown template %', p_template_id;
    END CASE;

    RETURN COALESCE(v_result, '{}'::jsonb);
END;
$$;

REVOKE ALL ON FUNCTION analytics_v2.get_indicator_block_for(uuid, text, text)
    FROM PUBLIC, authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.get_indicator_block_for(uuid, text, text)
    TO service_role;

COMMENT ON FUNCTION analytics_v2.get_indicator_block_for IS
    'Service-role dispatcher: fetches the dimension indicator block for the '
    'given (client_id, template_id) without requiring an authenticated JWT. '
    'Used by the Phase 4 report module + scheduler.';

COMMIT;
