CREATE OR REPLACE FUNCTION public.refresh_analytics_views()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'analytics_v2', 'public'
AS $$
DECLARE
  v_started_at  timestamptz := now();
  v_errors      text[]      := ARRAY[]::text[];
BEGIN
  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_resumo_dashboard: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_series_temporal;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_series_temporal: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_distribuicao_regional: ' || SQLERRM);
  END;

  BEGIN
    REFRESH MATERIALIZED VIEW analytics_v2.mv_ultimos_pedidos;
  EXCEPTION WHEN OTHERS THEN
    v_errors := array_append(v_errors, 'mv_ultimos_pedidos: ' || SQLERRM);
  END;

  RETURN jsonb_build_object(
    'refreshed_at',    now(),
    'duration_ms',     extract(milliseconds from (now() - v_started_at))::int,
    'views_refreshed', to_jsonb(ARRAY[
      'mv_resumo_dashboard',
      'mv_series_temporal',
      'mv_distribuicao_regional',
      'mv_ultimos_pedidos'
    ]),
    'errors', to_jsonb(v_errors)
  );
END;
$$;

COMMENT ON FUNCTION public.refresh_analytics_views() IS
  'Refreshes all four analytics_v2 materialized views in dependency order. Each view is wrapped in its own exception block so a single failure does not abort the rest. Returns a JSON summary with duration and any per-view errors. Meant to be called by a cron job immediately after run_incremental_etl completes.';
