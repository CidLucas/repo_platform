-- ─────────────────────────────────────────────────────────────────────────────
-- FASE 1 · Incremental refresh — 12h auto-sync
--
-- Design:
--   • run_etl_job() already reads watermark_column / last_watermark_value from
--     client_data_sources and builds a WHERE clause for incremental extraction.
--   • This migration adds the scheduler: a pg_cron job (every 12h) that enqueues
--     a reg_jobs row for each datasource that hasn't synced in the last 12 hours.
--   • Guard: skips datasources that already have a pending/running job.
--   • force_full_sync = false so watermark is always respected.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.enqueue_incremental_syncs()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_count integer := 0;
  v_row   record;
BEGIN
  FOR v_row IN
    SELECT cds.client_id,
           cds.credential_id::bigint AS credential_id
    FROM   public.client_data_sources cds
    WHERE  cds.sync_status IN ('synced', 'mapping_confirmed')
      AND (
        cds.last_synced_at IS NULL
        OR cds.last_synced_at < now() - interval '12 hours'
      )
      -- No in-flight job for this client
      AND NOT EXISTS (
        SELECT 1
        FROM   analytics_v2.reg_jobs rj
        WHERE  rj.client_id = cds.client_id
          AND  rj.job_type  = 'bigquery_sync'
          AND  rj.status    IN ('pending', 'running')
      )
      -- Credential must still exist and be active
      AND EXISTS (
        SELECT 1
        FROM   public.credencial_servico_externo cse
        WHERE  cse.id     = cds.credential_id
          AND  cse.ativo  = true
      )
  LOOP
    INSERT INTO analytics_v2.reg_jobs
      (client_id, job_type, status, sync_mode, input_params)
    VALUES (
      v_row.client_id,
      'bigquery_sync',
      'pending',
      'incremental',
      jsonb_build_object(
        'credential_id',   v_row.credential_id,
        'force_full_sync', false
      )
    );
    v_count := v_count + 1;
  END LOOP;

  RETURN v_count;
END;
$$;

-- Register pg_cron job: 02:00 and 14:00 UTC every day
SELECT cron.schedule(
  'enqueue_incremental_syncs_12h',
  '0 2,14 * * *',
  $$ SELECT analytics_v2.enqueue_incremental_syncs(); $$
);
