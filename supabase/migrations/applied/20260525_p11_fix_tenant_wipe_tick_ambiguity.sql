-- ============================================================================
-- P11 hotfix: column reference "table_fqn" is ambiguous
-- ============================================================================
-- O FOR-loop em admin.tenant_wipe_tick declarava `table_fqn` como OUT param
-- da função (RETURNS TABLE) e ao mesmo tempo selecionava da view
-- admin.v_wipe_target_tables que tem a coluna `table_fqn`. PL/pgSQL não
-- distinguia → ERRO em runtime no primeiro tick.
--
-- Fix: qualificar `table_fqn` com o alias da view (t.table_fqn) no WHERE/ORDER
-- BY do FOR. Mantém todo o restante igual ao P11 original.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION admin.tenant_wipe_tick(
  p_batch_size int DEFAULT 5000,
  p_max_seconds int DEFAULT 25
)
RETURNS TABLE(job_id uuid, table_fqn text, rows_deleted int, finished boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, admin
AS $$
DECLARE
  v_job          admin.tenant_wipe_jobs%ROWTYPE;
  v_target       record;
  v_rows         int;
  v_total_rows   int := 0;
  v_t0           timestamptz := clock_timestamp();
  v_t_batch      timestamptz;
  v_batch_no     int := 0;
  v_finished_job boolean := false;
  v_sql          text;
BEGIN
  SELECT * INTO v_job
  FROM admin.tenant_wipe_jobs
  WHERE status IN ('queued','running')
  ORDER BY (status='queued') DESC, COALESCE(started_at, created_at) ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF v_job.status = 'queued' THEN
    UPDATE admin.tenant_wipe_jobs
       SET status='running', started_at=now(), updated_at=now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;
    v_job.status := 'running';
    v_job.started_at := now();
  END IF;

  FOR v_target IN
    SELECT t.*
    FROM admin.v_wipe_target_tables t
    WHERE (v_job.current_table IS NULL)
       OR (t.table_fqn >= v_job.current_table)
    ORDER BY t.priority, t.table_fqn
  LOOP
    LOOP
      IF EXTRACT(EPOCH FROM (clock_timestamp() - v_t0)) > p_max_seconds THEN
        EXIT;
      END IF;

      v_t_batch := clock_timestamp();
      v_batch_no := v_batch_no + 1;

      v_sql := format(
        'WITH victim AS (
           SELECT ctid FROM %I.%I
           WHERE %I = $1
           LIMIT $2
         )
         DELETE FROM %I.%I t USING victim WHERE t.ctid = victim.ctid',
        v_target.child_schema, v_target.child_table, v_target.fk_column,
        v_target.child_schema, v_target.child_table
      );

      EXECUTE v_sql USING v_job.client_id, p_batch_size;
      GET DIAGNOSTICS v_rows = ROW_COUNT;
      v_total_rows := v_total_rows + v_rows;

      INSERT INTO admin.tenant_wipe_audit(job_id, table_name, batch_no, rows_deleted, duration_ms)
      VALUES (
        v_job.job_id, v_target.table_fqn, v_batch_no, v_rows,
        EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_t_batch))::int
      );

      job_id := v_job.job_id;
      table_fqn := v_target.table_fqn;
      rows_deleted := v_rows;
      finished := false;
      RETURN NEXT;

      EXIT WHEN v_rows = 0;

      PERFORM pg_sleep(0.05);
    END LOOP;

    UPDATE admin.tenant_wipe_jobs
       SET current_table = v_target.table_fqn,
           rows_deleted_total = rows_deleted_total + v_total_rows,
           updated_at = now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;

    EXIT WHEN EXTRACT(EPOCH FROM (clock_timestamp() - v_t0)) > p_max_seconds;
  END LOOP;

  PERFORM 1
    FROM admin.v_wipe_target_tables t
    WHERE admin._table_has_client(t.child_schema, t.child_table, t.fk_column, v_job.client_id)
    LIMIT 1;

  IF NOT FOUND THEN
    DROP TABLE IF EXISTS _users_to_delete;
    CREATE TEMP TABLE _users_to_delete ON COMMIT DROP AS
      SELECT user_id FROM public.client_users WHERE client_id = v_job.client_id;

    DELETE FROM vault.secrets
      WHERE name LIKE 'oauth_google_'    || v_job.client_id || '\_%' ESCAPE '\'
         OR name LIKE 'oauth_%_'         || v_job.client_id || '\_%' ESCAPE '\'
         OR name = 'bigquery_service_account_' || v_job.client_id
         OR name LIKE 'bigquery_'        || v_job.client_id || '\_%' ESCAPE '\'
         OR name LIKE 'integration_%\_'  || v_job.client_id || '%' ESCAPE '\';

    DELETE FROM public.clientes_blu WHERE client_id = v_job.client_id;

    DELETE FROM auth.users WHERE id IN (SELECT user_id FROM _users_to_delete);

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS bigquery_%s CASCADE', v_job.client_id);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Skipping FDW server drop for %: %', v_job.client_id, SQLERRM;
    END;

    UPDATE admin.tenant_wipe_jobs
       SET status='completed',
           progress_pct=100,
           completed_at=now(),
           updated_at=now()
     WHERE tenant_wipe_jobs.job_id = v_job.job_id;

    v_finished_job := true;
  END IF;

  job_id := v_job.job_id;
  table_fqn := COALESCE(v_target.table_fqn, '(end)');
  rows_deleted := 0;
  finished := v_finished_job;
  RETURN NEXT;
END;
$$;

REVOKE ALL ON FUNCTION admin.tenant_wipe_tick(int,int) FROM PUBLIC;

COMMIT;
