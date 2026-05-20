-- 1. Drop get_my_context_metrics() no-arg overload (frontend always passes p_period)
DROP FUNCTION IF EXISTS public.get_my_context_metrics();

-- 2. Drop update_bigquery_foreign_table_columns (dead — only in archive migrations)
DROP FUNCTION IF EXISTS public.update_bigquery_foreign_table_columns(text, jsonb);

-- 3. Drop create_bigquery_foreign_table(uuid overload) — all live code uses the bigint overload
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(text, text, text, uuid, text);

-- 4. Fix get_pendencias — correct semantic mapping (ETL jobs are infra, not business RFQs)
CREATE OR REPLACE FUNCTION public.get_pendencias()
RETURNS TABLE(kind text, title text, severity text, occurred_at timestamptz, target_route text)
LANGUAGE sql
STABLE
SET search_path TO 'analytics_v2', 'public'
AS $function$
SELECT
  CASE
    WHEN rj.job_type = 'connector_sync' THEN 'connector_error'
    WHEN rj.job_type = 'bigquery_sync'  THEN 'data_source_issue'
    WHEN rj.job_type = 'analytics_etl'  THEN 'etl_issue'
    ELSE 'system_issue'
  END AS kind,
  INITCAP(REPLACE(rj.job_type, '_', ' ')) || ': ' || COALESCE(rj.resource_type, 'Unknown') AS title,
  CASE
    WHEN rj.status = 'failed'  THEN 'error'
    WHEN rj.status = 'pending' THEN 'warning'
    ELSE 'info'
  END AS severity,
  rj.created_at AS occurred_at,
  CASE
    WHEN rj.job_type = 'connector_sync' THEN '/dashboard/connectors'
    WHEN rj.job_type IN ('bigquery_sync', 'analytics_etl') THEN '/dashboard/sources'
    ELSE '/dashboard'
  END AS target_route
FROM analytics_v2.reg_jobs rj
WHERE rj.client_id = public.get_my_client_id()
  AND (rj.status IN ('pending', 'failed') OR rj.error_message IS NOT NULL)
ORDER BY rj.created_at DESC;
$function$;

-- 5. Fix run_incremental_etl: use job_type='bigquery_sync' so process_pending_etl_jobs picks it up
CREATE OR REPLACE FUNCTION public.run_incremental_etl(
  p_hours_since_last_sync integer DEFAULT 20
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $$
DECLARE
  v_source    record;
  v_enqueued  integer := 0;
  v_skipped   integer := 0;
BEGIN
  FOR v_source IN
    SELECT
      cds.id              AS data_source_id,
      cds.client_id,
      cds.credential_id,
      cds.source_type,
      cds.resource_type,
      cds.watermark_column,
      cds.last_watermark_value,
      cds.last_synced_at
    FROM public.client_data_sources cds
    WHERE cds.sync_status IN ('ready', 'success', 'synced')
      AND (
        cds.last_synced_at IS NULL
        OR cds.last_synced_at < now() - (p_hours_since_last_sync || ' hours')::interval
      )
    ORDER BY cds.client_id, cds.resource_type
  LOOP
    -- Skip if a pending/running job already exists for this source
    IF EXISTS (
      SELECT 1 FROM analytics_v2.reg_jobs
      WHERE client_id     = v_source.client_id
        AND credential_id = v_source.credential_id
        AND job_type      = 'bigquery_sync'
        AND status IN ('pending', 'running')
    ) THEN
      v_skipped := v_skipped + 1;
      CONTINUE;
    END IF;

    INSERT INTO analytics_v2.reg_jobs (
      job_id, client_id, job_type, credential_id, resource_type,
      sync_mode, status, input_params, created_at, updated_at
    ) VALUES (
      gen_random_uuid(),
      v_source.client_id,
      'bigquery_sync',
      v_source.credential_id,
      v_source.resource_type,
      CASE WHEN v_source.last_watermark_value IS NOT NULL THEN 'incremental' ELSE 'full' END,
      'pending',
      jsonb_build_object(
        'data_source_id',       v_source.data_source_id,
        'source_type',          v_source.source_type,
        'watermark_column',     v_source.watermark_column,
        'last_watermark_value', v_source.last_watermark_value,
        'force_full_sync',      (v_source.last_watermark_value IS NULL),
        'requested_at',         now()
      ),
      now(),
      now()
    );

    v_enqueued := v_enqueued + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'enqueued', v_enqueued,
    'skipped',  v_skipped,
    'run_at',   now()
  );
END;
$$;

-- 6. Unique indexes for remaining two MVs so REFRESH MATERIALIZED VIEW CONCURRENTLY works everywhere
CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_series_temporal_pk
  ON analytics_v2.mv_series_temporal (client_id, data_periodo, tipo_grafico, dimensao);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_mv_ultimos_pedidos_pk
  ON analytics_v2.mv_ultimos_pedidos (client_id, pedido_id);
