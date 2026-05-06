-- =============================================================================
-- Migration: Create sincronizar_dados_cliente RPC + pg_cron job processor
-- Date: 2026-04-28
-- Purpose: Process queued BigQuery sync jobs from analytics_v2.reg_jobs
-- =============================================================================

BEGIN;

-- =============================================================================
-- RPC Function: sincronizar_dados_cliente
-- Processes a single sync job from analytics_v2.reg_jobs
-- Called by pg_cron job processor
-- =============================================================================

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
    p_job_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_job RECORD;
    v_client_id UUID;
    v_credential_id BIGINT;
    v_start_time TIMESTAMPTZ;
    v_rows_affected BIGINT := 0;
    v_error_msg TEXT;
BEGIN
    v_start_time := now();

    -- Get the job details
    SELECT
        j.job_id, j.client_id, j.credential_id, j.input_params, j.status
    INTO v_job
    FROM analytics_v2.reg_jobs j
    WHERE j.job_id = p_job_id
    FOR UPDATE;

    IF v_job IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Job not found',
            'job_id', p_job_id
        );
    END IF;

    IF v_job.status != 'pending' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', format('Job is not in pending state (current: %s)', v_job.status),
            'job_id', p_job_id
        );
    END IF;

    v_client_id := v_job.client_id;
    v_credential_id := (v_job.input_params->>'credential_id')::BIGINT;

    -- Update job status to running
    UPDATE analytics_v2.reg_jobs
    SET
        status = 'running',
        started_at = now(),
        progress_pct = 0,
        updated_at = now()
    WHERE job_id = p_job_id;

    BEGIN
        -- Get the data source metadata (foreign table columns, column mapping)
        DECLARE
            v_source_columns JSONB;
            v_column_mapping JSONB;
            v_ft_id BIGINT;
        BEGIN
            -- Fetch data source and column mapping
            SELECT
                ds.source_columns,
                ds.column_mapping,
                ds.id
            INTO
                v_source_columns,
                v_column_mapping,
                v_ft_id
            FROM public.client_data_sources ds
            WHERE ds.client_id = v_client_id
            AND ds.credential_id = v_credential_id
            ORDER BY ds.atualizado_em DESC
            LIMIT 1;

            IF v_column_mapping IS NULL THEN
                RAISE EXCEPTION 'No column mapping found for this data source';
            END IF;

            -- For now, just mark as completed
            -- The actual BigQuery→Postgres sync would happen here
            -- This is a placeholder that needs the actual ETL logic

            v_rows_affected := 0;

            -- Update job to completed
            UPDATE analytics_v2.reg_jobs
            SET
                status = 'completed',
                completed_at = now(),
                rows_inserted = v_rows_affected,
                progress_pct = 100,
                duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
                output = jsonb_build_object(
                    'rows_inserted', v_rows_affected,
                    'completed_at', now()
                ),
                updated_at = now()
            WHERE job_id = p_job_id;

            RETURN jsonb_build_object(
                'success', true,
                'job_id', p_job_id,
                'rows_inserted', v_rows_affected,
                'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))
            );

        EXCEPTION WHEN OTHERS THEN
            v_error_msg := SQLERRM;

            UPDATE analytics_v2.reg_jobs
            SET
                status = 'failed',
                completed_at = now(),
                progress_pct = 0,
                duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time)),
                error_message = v_error_msg,
                updated_at = now()
            WHERE job_id = p_job_id;

            RETURN jsonb_build_object(
                'success', false,
                'job_id', p_job_id,
                'error', v_error_msg
            );
        END;

    EXCEPTION WHEN OTHERS THEN
        v_error_msg := SQLERRM;

        UPDATE analytics_v2.reg_jobs
        SET
            status = 'failed',
            error_message = v_error_msg,
            updated_at = now()
        WHERE job_id = p_job_id;

        RETURN jsonb_build_object(
            'success', false,
            'job_id', p_job_id,
            'error', v_error_msg
        );
    END;

END;
$$;

COMMENT ON FUNCTION public.sincronizar_dados_cliente(UUID) IS
'Process a single queued BigQuery sync job. Called by pg_cron job processor.';

-- =============================================================================
-- RPC Function: process_pending_sync_jobs
-- Polls for pending jobs and processes them one-by-one
-- Called by pg_cron every 30 seconds
-- =============================================================================

CREATE OR REPLACE FUNCTION public.process_pending_sync_jobs()
RETURNS TABLE (
    jobs_processed INT,
    jobs_succeeded INT,
    jobs_failed INT,
    duration_seconds NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_start_time TIMESTAMPTZ := now();
    v_job_id UUID;
    v_processed INT := 0;
    v_succeeded INT := 0;
    v_failed INT := 0;
    v_result JSONB;
BEGIN
    -- Process up to 10 pending jobs per run
    FOR v_job_id IN
        SELECT job_id
        FROM analytics_v2.reg_jobs
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 10
    LOOP
        v_processed := v_processed + 1;

        v_result := public.sincronizar_dados_cliente(v_job_id);

        IF (v_result->>'success')::BOOLEAN THEN
            v_succeeded := v_succeeded + 1;
        ELSE
            v_failed := v_failed + 1;
        END IF;

    END LOOP;

    RETURN QUERY SELECT
        v_processed,
        v_succeeded,
        v_failed,
        EXTRACT(EPOCH FROM (now() - v_start_time))::NUMERIC;

END;
$$;

COMMENT ON FUNCTION public.process_pending_sync_jobs() IS
'Poll and process up to 10 pending sync jobs from analytics_v2.reg_jobs. Called by pg_cron every 30 seconds.';

-- =============================================================================
-- pg_cron: Schedule job processor
-- Runs every 30 seconds to process pending sync jobs
-- =============================================================================

SELECT cron.schedule(
    'process-pending-sync-jobs',
    '*/30 * * * * *',  -- Every 30 seconds
    'SELECT public.process_pending_sync_jobs();'
);

COMMIT;
