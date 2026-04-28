-- Migration: Create missing RPC functions for dashboard analytics
-- Purpose: Expose metrics queries as callable functions
-- Created: 2026-04-28

-- ============================================================================
-- RPC FUNCTION: get_nps_score
-- ============================================================================
-- Returns NPS metrics from nps_responses within a rolling window

CREATE OR REPLACE FUNCTION public.get_nps_score(p_window_days INT DEFAULT 90)
RETURNS TABLE(
  score NUMERIC,
  total_responses BIGINT,
  promoters BIGINT,
  passives BIGINT,
  detractors BIGINT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
SELECT
  CASE
    WHEN COUNT(*) > 0
    THEN ROUND(
      ((COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::NUMERIC -
        COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::NUMERIC) /
       COUNT(*)::NUMERIC * 100), 1)
    ELSE NULL::NUMERIC
  END AS score,

  COUNT(*)::BIGINT AS total_responses,

  COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::BIGINT AS promoters,
  COALESCE(SUM(CASE WHEN score >= 7 AND score <= 8 THEN 1 ELSE 0 END), 0)::BIGINT AS passives,
  COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::BIGINT AS detractors

FROM public.nps_responses
WHERE client_id = public.get_my_client_id()
  AND created_at >= CURRENT_TIMESTAMP - (p_window_days || ' days')::INTERVAL;
$$;

-- ============================================================================
-- RPC FUNCTION: get_recent_activity
-- ============================================================================
-- Returns recent audit events for the current client

CREATE OR REPLACE FUNCTION public.get_recent_activity(p_limit INT DEFAULT 10)
RETURNS TABLE(
  kind TEXT,
  title TEXT,
  subtitle TEXT,
  occurred_at TIMESTAMPTZ,
  severity TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
SELECT
  -- Map audit action to UI-friendly kind
  CASE
    WHEN action = 'CREATE' THEN 'ingestion'
    WHEN action = 'UPDATE' THEN 'agent_session'
    WHEN action = 'DELETE' THEN 'error'
    ELSE 'info'
  END AS kind,

  -- Title from entity_type + action
  UPPER(entity_type) || ' ' || action AS title,

  -- Subtitle from payload JSON (if available)
  (payload->>'description')::TEXT AS subtitle,

  created_at AS occurred_at,

  -- Severity based on action type
  CASE
    WHEN action = 'DELETE' THEN 'error'
    WHEN action = 'UPDATE' THEN 'warning'
    ELSE 'info'
  END AS severity

FROM public.audit_log
WHERE client_id = public.get_my_client_id()
ORDER BY created_at DESC
LIMIT p_limit;
$$;

-- ============================================================================
-- RPC FUNCTION: get_my_dashboard_kpis
-- ============================================================================
-- Returns KPI configuration for the current client's dashboard

CREATE OR REPLACE FUNCTION public.get_my_dashboard_kpis()
RETURNS TABLE(
  dimension TEXT,
  slot_index INT,
  slug TEXT,
  label TEXT,
  unit TEXT,
  formula TEXT,
  data_status TEXT,
  tier_required TEXT,
  is_enabled BOOLEAN
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
SELECT
  ck.dimension,
  ROW_NUMBER() OVER (PARTITION BY ck.dimension ORDER BY kc.sort_order) AS slot_index,
  kc.slug,
  kc.label,
  kc.unit,
  kc.formula,
  kc.data_status,
  kc.tier_required,
  COALESCE(ck.slug IS NOT NULL, FALSE) AS is_enabled

FROM public.kpi_catalog kc
LEFT JOIN public.client_dimension_kpis ck
  ON ck.slug = kc.slug
  AND ck.client_id = public.get_my_client_id()
  AND ck.dimension = kc.dimension

WHERE kc.is_active = TRUE
ORDER BY kc.dimension, kc.sort_order;
$$;

-- ============================================================================
-- RPC FUNCTION: get_pendencias
-- ============================================================================
-- Returns pending items/issues (failed jobs, connector errors, etc.)

CREATE OR REPLACE FUNCTION public.get_pendencias()
RETURNS TABLE(
  kind TEXT,
  title TEXT,
  severity TEXT,
  occurred_at TIMESTAMPTZ,
  target_route TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = 'analytics_v2'
AS $$
SELECT
  -- Map job status to kind
  CASE
    WHEN rj.job_type = 'connector_sync' THEN 'connector_error'
    WHEN rj.job_type = 'bigquery_sync' THEN 'data_source_issue'
    WHEN rj.job_type = 'analytics_etl' THEN 'rfq_pending'
    ELSE 'rfq_pending'
  END AS kind,

  -- Title with job type
  'Job: ' || rj.job_type || ' - ' || COALESCE(rj.resource_type, 'Unknown') AS title,

  -- Severity: error if failed, warning if pending
  CASE
    WHEN rj.status = 'failed' THEN 'error'
    WHEN rj.status = 'pending' THEN 'warning'
    ELSE 'info'
  END AS severity,

  rj.created_at AS occurred_at,

  -- Navigation route based on job type
  CASE
    WHEN rj.job_type = 'connector_sync' THEN '/dashboard/connectors'
    WHEN rj.job_type = 'bigquery_sync' THEN '/dashboard/sources'
    ELSE '/dashboard'
  END AS target_route

FROM analytics_v2.reg_jobs rj
WHERE rj.client_id = public.get_my_client_id()
  AND (rj.status IN ('pending', 'failed') OR rj.error_message IS NOT NULL)
ORDER BY rj.created_at DESC;
$$;

-- ============================================================================
-- RPC FUNCTION: get_agent_runs_today
-- ============================================================================
-- Returns agent task statistics for today

CREATE OR REPLACE FUNCTION public.get_agent_runs_today()
RETURNS TABLE(
  total INT,
  by_agent JSONB
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = 'analytics_v2'
AS $$
SELECT
  COUNT(*)::INT AS total,
  JSONB_OBJECT_AGG(
    COALESCE(resource_type, 'unknown'),
    run_count
  ) AS by_agent

FROM (
  SELECT
    resource_type,
    COUNT(*)::INT AS run_count
  FROM analytics_v2.reg_jobs
  WHERE client_id = public.get_my_client_id()
    AND job_type LIKE '%agent%'
    AND DATE(created_at) = CURRENT_DATE
  GROUP BY resource_type
) subquery;
$$;

-- ============================================================================
-- RPC FUNCTION: get_my_insights
-- ============================================================================
-- Returns AI-generated insights for the current client

CREATE OR REPLACE FUNCTION public.get_my_insights(
  p_limit INT DEFAULT 5,
  p_status TEXT DEFAULT 'active'
)
RETURNS TABLE(
  id UUID,
  run_date TIMESTAMPTZ,
  dimension TEXT,
  kpi TEXT,
  severity TEXT,
  title TEXT,
  observation TEXT,
  recommendation TEXT,
  metric_value NUMERIC,
  baseline_value NUMERIC,
  variance_pct NUMERIC,
  status TEXT,
  created_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
SELECT
  ci.id,
  ci.run_date,
  ci.dimension,
  ci.kpi,
  ci.severity,
  ci.title,
  ci.observation,
  ci.recommendation,
  ci.metric_value,
  ci.baseline_value,
  ci.variance_pct,
  ci.status,
  ci.created_at

FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND ci.status = p_status
ORDER BY ci.created_at DESC
LIMIT p_limit;
$$;

-- ============================================================================
-- GRANTS
-- ============================================================================
-- Grant execute permissions to authenticated users

GRANT EXECUTE ON FUNCTION public.get_nps_score(INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_recent_activity(INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_my_dashboard_kpis() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_pendencias() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_agent_runs_today() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_my_insights(INT, TEXT) TO authenticated;
