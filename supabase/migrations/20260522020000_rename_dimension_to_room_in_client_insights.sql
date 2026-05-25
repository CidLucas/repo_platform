-- Migration: rename dimension → room in client_insights
-- Maps old values: finance→financeiro, commercial→clientes, inventory→compras, supply→compras
-- Also updates RPCs: record_insight, get_my_insights to use room + adds p_room filter

BEGIN;

-- 1. Add room column, populate from dimension, then drop dimension
ALTER TABLE public.client_insights ADD COLUMN room text;

UPDATE public.client_insights
SET room = CASE dimension
  WHEN 'finance'     THEN 'financeiro'
  WHEN 'commercial'  THEN 'clientes'
  WHEN 'inventory'   THEN 'compras'
  WHEN 'supply'      THEN 'compras'
  ELSE dimension  -- fallback: keep as-is for unknown values
END;

ALTER TABLE public.client_insights DROP COLUMN dimension;

-- 2. Drop + recreate unique index that used dimension
DROP INDEX IF EXISTS client_insights_client_run_dim_kpi_idx;

CREATE UNIQUE INDEX client_insights_client_run_room_kpi_idx
  ON public.client_insights (client_id, run_date, room, kpi)
  WHERE run_date IS NOT NULL AND kpi IS NOT NULL;

-- 3. Recreate record_insight with p_dimension renamed to p_room + new slug values
CREATE OR REPLACE FUNCTION public.record_insight(
  p_client_id      uuid,
  p_room           text,              -- was: p_dimension
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
  p_prompt_version text    DEFAULT NULL,
  -- backward-compat alias kept so old callers still work
  p_dimension      text    DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id       uuid;
  v_severity text;
  v_room     text;
BEGIN
  -- Normalise severity
  v_severity := COALESCE(p_severity, 'info');
  IF v_severity NOT IN ('info', 'warning', 'error') THEN
    v_severity := 'info';
  END IF;

  -- Support old p_dimension callers: map to room slug if p_room not given
  v_room := COALESCE(p_room, CASE p_dimension
    WHEN 'finance'    THEN 'financeiro'
    WHEN 'commercial' THEN 'clientes'
    WHEN 'inventory'  THEN 'compras'
    WHEN 'supply'     THEN 'compras'
    ELSE p_dimension
  END, 'financeiro');

  INSERT INTO public.client_insights (
    id, client_id, room, kpi,
    title, observation, recommendation,
    severity, metric_value, baseline_value, variance_pct,
    run_date, prompt_version,
    body, generated_at
  )
  VALUES (
    gen_random_uuid(), p_client_id, v_room, p_kpi,
    p_title, p_observation, p_recommendation,
    v_severity, p_metric_value, p_baseline_value, p_variance_pct,
    COALESCE(p_run_date, CURRENT_DATE), p_prompt_version,
    p_observation,
    now()
  )
  ON CONFLICT (client_id, run_date, room, kpi)
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

-- 4. Recreate get_my_insights with optional p_room filter
CREATE OR REPLACE FUNCTION public.get_my_insights(
  p_limit  integer DEFAULT 5,
  p_status text    DEFAULT 'active',
  p_room   text    DEFAULT NULL
)
RETURNS TABLE(
  id             uuid,
  run_date       timestamp with time zone,
  room           text,
  kpi            text,
  severity       text,
  title          text,
  observation    text,
  recommendation text,
  metric_value   numeric,
  baseline_value numeric,
  variance_pct   numeric,
  status         text,
  created_at     timestamp with time zone
)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
SELECT
  ci.id,
  COALESCE(ci.run_date::timestamptz, ci.generated_at) AS run_date,
  ci.room,
  ci.kpi,
  ci.severity,
  ci.title,
  COALESCE(ci.observation, ci.body, '')               AS observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at                                     AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
        (p_status = 'active'    AND NOT ci.dismissed)
     OR (p_status = 'dismissed' AND     ci.dismissed)
     OR  p_status NOT IN ('active', 'dismissed')
  )
  AND (p_room IS NULL OR ci.room = p_room)
ORDER BY ci.generated_at DESC
LIMIT p_limit;
$$;

COMMIT;
