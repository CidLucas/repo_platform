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
    WHERE cds.sync_status IN ('ready', 'success')
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
        AND resource_type = v_source.resource_type
        AND job_type      = 'analytics_etl'
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
      'analytics_etl',
      v_source.credential_id,
      v_source.resource_type,
      CASE WHEN v_source.last_watermark_value IS NOT NULL THEN 'incremental' ELSE 'full' END,
      'pending',
      jsonb_build_object(
        'data_source_id',       v_source.data_source_id,
        'source_type',          v_source.source_type,
        'watermark_column',     v_source.watermark_column,
        'last_watermark_value', v_source.last_watermark_value,
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

COMMENT ON FUNCTION public.run_incremental_etl(integer) IS
  'Enqueues analytics_etl jobs in reg_jobs for every active data source not synced within the last p_hours_since_last_sync hours. Uses watermark_column/last_watermark_value for incremental loads; falls back to full load when no watermark exists. The Python backend picks up pending jobs and executes the actual data movement.';
