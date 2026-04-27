-- Migration: Phase 2 (I2.1, I2.2) — client_insights table + supporting RPCs.
--
-- Adds the canonical store for per-tenant insights produced by the nightly
-- `routine.daily_insights` worker (libs/vizu_agent_framework/routines/daily_insights.py)
-- and read/dismiss RPCs consumed by the dashboard HomePage InsightsFeed.
--
-- Design notes
-- ─────────────────────────────────────────────────────────────────────
-- • `status` lifecycle: 'active' → 'dismissed' (user) | 'expired' (>7d)
-- • RLS: SELECT/UPDATE scoped to client via get_my_client_id();
--   INSERT denied for authenticated — only the routine (service_role) writes.
-- • Worker idempotency: (client_id, run_date, kpi) UNIQUE prevents dup runs.
-- • Severity mirrors the dashboard pendência scale (info/warning/error).

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Table
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.client_insights (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       uuid        NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  run_date        date        NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo')::date,
  dimension       text        NOT NULL CHECK (dimension IN (
                    'finance', 'commercial', 'inventory', 'supply', 'marketing', 'operations'
                  )),
  kpi             text        NOT NULL,
  severity        text        NOT NULL DEFAULT 'info'
                    CHECK (severity IN ('info', 'warning', 'error')),
  title           text        NOT NULL,
  observation     text        NOT NULL,
  recommendation  text,
  metric_value    numeric,
  baseline_value  numeric,
  variance_pct    numeric,
  payload         jsonb       NOT NULL DEFAULT '{}'::jsonb,
  status          text        NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'dismissed', 'expired')),
  source          text        NOT NULL DEFAULT 'routine.daily_insights',
  prompt_version  int,
  dismissed_at    timestamptz,
  dismissed_by    uuid        REFERENCES auth.users(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Idempotency: one insight per (client, run_date, kpi). The worker upserts.
CREATE UNIQUE INDEX IF NOT EXISTS client_insights_dedup_idx
  ON public.client_insights (client_id, run_date, kpi);

CREATE INDEX IF NOT EXISTS client_insights_active_idx
  ON public.client_insights (client_id, status, created_at DESC)
  WHERE status = 'active';

-- updated_at trigger (reuse helper pattern from other tables)
CREATE OR REPLACE FUNCTION public.tg_client_insights_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS client_insights_set_updated_at ON public.client_insights;
CREATE TRIGGER client_insights_set_updated_at
  BEFORE UPDATE ON public.client_insights
  FOR EACH ROW EXECUTE FUNCTION public.tg_client_insights_set_updated_at();

-- ─────────────────────────────────────────────────────────────────────
-- 2. RLS
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE public.client_insights ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS client_insights_select ON public.client_insights;
CREATE POLICY client_insights_select ON public.client_insights
  FOR SELECT TO authenticated
  USING (client_id::text = public.get_my_client_id());

-- Direct INSERT denied for authenticated — only service-role workers may write.
DROP POLICY IF EXISTS client_insights_insert ON public.client_insights;
CREATE POLICY client_insights_insert ON public.client_insights
  FOR INSERT TO authenticated WITH CHECK (false);

-- UPDATE allowed only for status transitions to 'dismissed' on own rows. The
-- dismiss_insight() RPC (SECURITY DEFINER) is the canonical write path; this
-- policy is a safety net.
DROP POLICY IF EXISTS client_insights_update ON public.client_insights;
CREATE POLICY client_insights_update ON public.client_insights
  FOR UPDATE TO authenticated
  USING (client_id::text = public.get_my_client_id())
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_insights_delete ON public.client_insights;
CREATE POLICY client_insights_delete ON public.client_insights
  FOR DELETE TO authenticated USING (false);

DROP POLICY IF EXISTS client_insights_service_role ON public.client_insights;
CREATE POLICY client_insights_service_role ON public.client_insights
  FOR ALL TO service_role USING (true) WITH CHECK (true);

GRANT SELECT, UPDATE ON public.client_insights TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 3. Read RPC — get_my_insights(p_limit, p_status)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_my_insights(
  p_limit  int  DEFAULT 5,
  p_status text DEFAULT 'active'
)
RETURNS TABLE (
  id             uuid,
  run_date       date,
  dimension      text,
  kpi            text,
  severity       text,
  title          text,
  observation    text,
  recommendation text,
  metric_value   numeric,
  baseline_value numeric,
  variance_pct   numeric,
  status         text,
  created_at     timestamptz
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
  SELECT
    ci.id, ci.run_date, ci.dimension, ci.kpi, ci.severity,
    ci.title, ci.observation, ci.recommendation,
    ci.metric_value, ci.baseline_value, ci.variance_pct,
    ci.status, ci.created_at
  FROM public.client_insights ci
  WHERE ci.client_id::text = public.get_my_client_id()
    AND (p_status IS NULL OR ci.status = p_status)
  ORDER BY
    CASE ci.severity WHEN 'error' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
    ci.created_at DESC
  LIMIT GREATEST(COALESCE(p_limit, 5), 1);
$$;

GRANT EXECUTE ON FUNCTION public.get_my_insights(int, text) TO authenticated;

COMMENT ON FUNCTION public.get_my_insights IS
  'Phase 2 (I2.2): list insights for the current tenant ordered by severity then recency.';

-- ─────────────────────────────────────────────────────────────────────
-- 4. Dismiss RPC — dismiss_insight(p_insight_id)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.dismiss_insight(p_insight_id uuid)
RETURNS public.client_insights
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_my_client text := public.get_my_client_id();
  v_user      uuid := auth.uid();
  v_row       public.client_insights;
BEGIN
  IF v_my_client IS NULL OR v_my_client = '' THEN
    RAISE EXCEPTION 'dismiss_insight: caller has no client_id claim';
  END IF;

  UPDATE public.client_insights
     SET status       = 'dismissed',
         dismissed_at = now(),
         dismissed_by = v_user
   WHERE id = p_insight_id
     AND client_id::text = v_my_client
     AND status = 'active'
  RETURNING * INTO v_row;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'dismiss_insight: insight % not found, not yours, or not active',
                    p_insight_id;
  END IF;

  PERFORM public.record_audit(
    p_action    => 'insight.dismiss',
    p_payload   => jsonb_build_object('insight_id', v_row.id, 'kpi', v_row.kpi, 'dimension', v_row.dimension),
    p_resource  => 'client_insights',
    p_resource_id => v_row.id::text,
    p_actor_kind => 'user',
    p_outcome   => 'success'
  );

  RETURN v_row;
END;
$$;

GRANT EXECUTE ON FUNCTION public.dismiss_insight(uuid) TO authenticated;

COMMENT ON FUNCTION public.dismiss_insight IS
  'Phase 2 (I2.2): mark an insight as dismissed. RLS-equivalent via JWT-derived client_id.';

-- ─────────────────────────────────────────────────────────────────────
-- 5. Worker write RPC — record_insight(...) (service-role only)
-- ─────────────────────────────────────────────────────────────────────
--
-- The Python worker calls this RPC via the service-role client. Going through
-- a SECURITY DEFINER RPC keeps the dedup-on-conflict logic in one place and
-- makes the audit trail consistent with other mutating tools.

CREATE OR REPLACE FUNCTION public.record_insight(
  p_client_id      uuid,
  p_dimension      text,
  p_kpi            text,
  p_title          text,
  p_observation    text,
  p_severity       text          DEFAULT 'info',
  p_recommendation text          DEFAULT NULL,
  p_metric_value   numeric       DEFAULT NULL,
  p_baseline_value numeric       DEFAULT NULL,
  p_variance_pct   numeric       DEFAULT NULL,
  p_payload        jsonb         DEFAULT '{}'::jsonb,
  p_run_date       date          DEFAULT NULL,
  p_prompt_version int           DEFAULT NULL
)
RETURNS public.client_insights
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row      public.client_insights;
  v_run_date date := COALESCE(p_run_date, (now() AT TIME ZONE 'America/Sao_Paulo')::date);
BEGIN
  IF auth.uid() IS NOT NULL THEN
    RAISE EXCEPTION 'record_insight: only service-role callers may invoke';
  END IF;

  INSERT INTO public.client_insights (
    client_id, run_date, dimension, kpi, severity,
    title, observation, recommendation,
    metric_value, baseline_value, variance_pct,
    payload, prompt_version
  ) VALUES (
    p_client_id, v_run_date, p_dimension, p_kpi, COALESCE(p_severity, 'info'),
    p_title, p_observation, p_recommendation,
    p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_payload, '{}'::jsonb), p_prompt_version
  )
  ON CONFLICT (client_id, run_date, kpi) DO UPDATE
     SET dimension      = EXCLUDED.dimension,
         severity       = EXCLUDED.severity,
         title          = EXCLUDED.title,
         observation    = EXCLUDED.observation,
         recommendation = EXCLUDED.recommendation,
         metric_value   = EXCLUDED.metric_value,
         baseline_value = EXCLUDED.baseline_value,
         variance_pct   = EXCLUDED.variance_pct,
         payload        = EXCLUDED.payload,
         prompt_version = EXCLUDED.prompt_version,
         status         = CASE WHEN public.client_insights.status = 'dismissed'
                                THEN public.client_insights.status
                                ELSE 'active' END,
         updated_at     = now()
  RETURNING * INTO v_row;

  RETURN v_row;
END;
$$;

REVOKE ALL ON FUNCTION public.record_insight(uuid, text, text, text, text, text, text, numeric, numeric, numeric, jsonb, date, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_insight(uuid, text, text, text, text, text, text, numeric, numeric, numeric, jsonb, date, int) TO service_role;

COMMENT ON FUNCTION public.record_insight IS
  'Phase 2 (I2.1): upsert a routine-generated insight. Service-role only.';

-- ─────────────────────────────────────────────────────────────────────
-- 6. Expire stale insights — sweeper
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.expire_stale_insights(p_max_age_days int DEFAULT 7)
RETURNS int
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_count int;
BEGIN
  UPDATE public.client_insights
     SET status = 'expired'
   WHERE status = 'active'
     AND created_at < now() - make_interval(days => GREATEST(p_max_age_days, 1));
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;

REVOKE ALL ON FUNCTION public.expire_stale_insights(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.expire_stale_insights(int) TO service_role;

COMMENT ON FUNCTION public.expire_stale_insights IS
  'Phase 2 (I2.1): mark active insights older than N days as expired. Run nightly alongside daily_insights.';

-- ─────────────────────────────────────────────────────────────────────
-- 7. Service-role wrapper for the dimension RPCs
-- ─────────────────────────────────────────────────────────────────────
--
-- The Phase 1 indicator RPCs (analytics_v2.get_<dim>_indicators) gate on
-- `public.get_my_client_id()`, which derives client_id from the JWT email.
-- The daily_insights worker runs under service-role with no JWT, so it cannot
-- call those RPCs directly. This wrapper forges a transaction-local JWT claim
-- so the underlying RPC sees the requested tenant.
--
-- Service-role only — DO NOT expose to authenticated. Otherwise any user could
-- read another tenant's KPIs.

CREATE OR REPLACE FUNCTION analytics_v2.get_indicators_for_client(
  p_client_id uuid,
  p_dimension text,
  p_period    text DEFAULT '30d'
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = analytics_v2, public, pg_temp
AS $$
DECLARE
  v_email text;
  v_row   jsonb;
BEGIN
  IF auth.uid() IS NOT NULL THEN
    RAISE EXCEPTION 'get_indicators_for_client: service-role callers only';
  END IF;

  SELECT email INTO v_email
    FROM public.clientes_vizu
   WHERE client_id = p_client_id;

  IF v_email IS NULL THEN
    RETURN '{}'::jsonb;
  END IF;

  -- Transaction-local JWT claim so get_my_client_id() resolves to p_client_id.
  PERFORM set_config(
    'request.jwt.claims',
    json_build_object('email', v_email, 'sub', p_client_id::text)::text,
    true
  );

  IF p_dimension = 'finance' THEN
    SELECT to_jsonb(t) INTO v_row FROM analytics_v2.get_finance_indicators(p_period) t LIMIT 1;
  ELSIF p_dimension = 'commercial' THEN
    SELECT to_jsonb(t) INTO v_row FROM analytics_v2.get_commercial_indicators(p_period) t LIMIT 1;
  ELSIF p_dimension = 'inventory' THEN
    SELECT to_jsonb(t) INTO v_row FROM analytics_v2.get_inventory_indicators(p_period) t LIMIT 1;
  ELSIF p_dimension = 'supply' THEN
    SELECT to_jsonb(t) INTO v_row FROM analytics_v2.get_supply_indicators(p_period) t LIMIT 1;
  ELSIF p_dimension = 'marketing' THEN
    SELECT to_jsonb(t) INTO v_row FROM analytics_v2.get_marketing_indicators(p_period) t LIMIT 1;
  ELSE
    RAISE EXCEPTION 'get_indicators_for_client: unknown dimension %', p_dimension;
  END IF;

  RETURN COALESCE(v_row, '{}'::jsonb);
END;
$$;

REVOKE ALL ON FUNCTION analytics_v2.get_indicators_for_client(uuid, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION analytics_v2.get_indicators_for_client(uuid, text, text) TO service_role;

COMMENT ON FUNCTION analytics_v2.get_indicators_for_client IS
  'Phase 2 (I2.1): service-role helper to read dimension KPIs for a specific tenant. Forges JWT claim transaction-locally so the underlying RPCs gate on the right client_id.';

COMMIT;
