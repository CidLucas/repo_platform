-- ─────────────────────────────────────────────────────────────────────────────
-- Fix client_insights schema to support the full daily_insights pipeline.
--
-- Problems fixed:
--   1. Table was missing kpi, observation, recommendation, metric_value,
--      baseline_value, variance_pct, run_date, prompt_version columns.
--   2. record_insight() had wrong signature (p_title, p_content, p_severity,
--      p_data) — daily_insights.py calls it with 13 named params.
--   3. get_my_insights() returned stubs (''::TEXT, NULL::NUMERIC) because
--      the columns didn't exist yet.
--   4. Severity constraint allowed 'critical' but daily_insights emits 'error'.
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. Add missing columns ───────────────────────────────────────────────────

ALTER TABLE public.client_insights
  ADD COLUMN IF NOT EXISTS kpi            text,
  ADD COLUMN IF NOT EXISTS observation    text,
  ADD COLUMN IF NOT EXISTS recommendation text,
  ADD COLUMN IF NOT EXISTS metric_value   numeric,
  ADD COLUMN IF NOT EXISTS baseline_value numeric,
  ADD COLUMN IF NOT EXISTS variance_pct   numeric,
  ADD COLUMN IF NOT EXISTS run_date       date,
  ADD COLUMN IF NOT EXISTS prompt_version text;

-- Backfill observation from body for any existing rows
UPDATE public.client_insights
SET observation = body
WHERE observation IS NULL AND body IS NOT NULL;


-- ── 2. Fix severity constraint ('error' replaces 'critical') ─────────────────
--
-- daily_insights.py validates severity ∈ {'info','warning','error'}.
-- The old constraint used 'critical' which would reject all 'error' rows.

ALTER TABLE public.client_insights
  DROP CONSTRAINT IF EXISTS client_insights_severity_check;

ALTER TABLE public.client_insights
  ADD CONSTRAINT client_insights_severity_check
  CHECK (severity IN ('info', 'warning', 'error'));


-- ── 3. Idempotency index for upsert by (client_id, run_date, dimension, kpi) ─
--
-- Partial index (WHERE run_date IS NOT NULL AND kpi IS NOT NULL) so that
-- old rows without these fields are not affected. The ON CONFLICT clause
-- in record_insight() mirrors this predicate exactly.

CREATE UNIQUE INDEX IF NOT EXISTS idx_insights_upsert
  ON public.client_insights (client_id, run_date, dimension, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL;


-- ── 4. Replace record_insight() with correct 13-param service-role signature ──
--
-- Old signature: (p_title, p_content, p_severity, p_data)
-- New signature matches daily_insights._record_insight() exactly.
-- SECURITY DEFINER so the routine can write on behalf of any tenant
-- without per-request JWT.

DROP FUNCTION IF EXISTS public.record_insight(text, text, text, jsonb);

CREATE OR REPLACE FUNCTION public.record_insight(
  p_client_id      uuid,
  p_dimension      text,
  p_kpi            text,
  p_title          text,
  p_observation    text,
  p_severity       text    DEFAULT 'info',
  p_recommendation text    DEFAULT NULL,
  p_metric_value   numeric DEFAULT NULL,
  p_baseline_value numeric DEFAULT NULL,
  p_variance_pct   numeric DEFAULT NULL,
  p_payload        jsonb   DEFAULT NULL,
  p_run_date       date    DEFAULT CURRENT_DATE,
  p_prompt_version text    DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id       uuid;
  v_severity text;
BEGIN
  -- Normalise severity; coerce unknown values to 'info' rather than failing
  v_severity := lower(COALESCE(p_severity, 'info'));
  IF v_severity NOT IN ('info', 'warning', 'error') THEN
    v_severity := 'info';
  END IF;

  INSERT INTO public.client_insights (
    id, client_id, dimension, kpi,
    title, observation, recommendation,
    severity, metric_value, baseline_value, variance_pct,
    run_date, prompt_version,
    body,          -- keep body in sync for backwards-compat queries
    generated_at
  )
  VALUES (
    gen_random_uuid(), p_client_id, p_dimension, p_kpi,
    p_title, p_observation, p_recommendation,
    v_severity, p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_run_date, CURRENT_DATE), p_prompt_version,
    p_observation,
    now()
  )
  ON CONFLICT (client_id, run_date, dimension, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL
  DO UPDATE SET
    title           = EXCLUDED.title,
    observation     = EXCLUDED.observation,
    body            = EXCLUDED.observation,
    recommendation  = EXCLUDED.recommendation,
    severity        = EXCLUDED.severity,
    metric_value    = EXCLUDED.metric_value,
    baseline_value  = EXCLUDED.baseline_value,
    variance_pct    = EXCLUDED.variance_pct,
    prompt_version  = EXCLUDED.prompt_version,
    generated_at    = now(),
    dismissed       = false,
    dismissed_at    = NULL
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.record_insight(uuid,text,text,text,text,text,text,numeric,numeric,numeric,jsonb,date,text)
  TO anon, authenticated, service_role;


-- ── 5. Update get_my_insights() to read real columns ─────────────────────────
--
-- Previous version returned stubs (''::TEXT AS kpi, NULL::NUMERIC, etc.)
-- because the columns didn't exist. Now reads actual data.
-- COALESCE(observation, body) ensures rows inserted before this migration
-- are still returned correctly.

CREATE OR REPLACE FUNCTION public.get_my_insights(
  p_limit  integer DEFAULT 5,
  p_status text    DEFAULT 'active'
)
RETURNS TABLE (
  id              uuid,
  run_date        timestamptz,
  dimension       text,
  kpi             text,
  severity        text,
  title           text,
  observation     text,
  recommendation  text,
  metric_value    numeric,
  baseline_value  numeric,
  variance_pct    numeric,
  status          text,
  created_at      timestamptz
)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
SELECT
  ci.id,
  COALESCE(ci.run_date::timestamptz, ci.generated_at)  AS run_date,
  ci.dimension,
  ci.kpi,
  ci.severity,
  ci.title,
  COALESCE(ci.observation, ci.body, '')                 AS observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at                                       AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
        (p_status = 'active'    AND NOT ci.dismissed)
     OR (p_status = 'dismissed' AND     ci.dismissed)
     OR  p_status NOT IN ('active', 'dismissed')
  )
ORDER BY ci.generated_at DESC
LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_my_insights(integer, text)
  TO anon, authenticated, service_role;
