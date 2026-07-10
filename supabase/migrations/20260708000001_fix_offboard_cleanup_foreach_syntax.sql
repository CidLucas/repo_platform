-- Fix offboard_cleanup_nightly pg_cron job: invalid FOREACH...END FOREACH (2026-07-08)
--
-- The job (jobid=13, schedule '0 3 * * *') has failed every single night since
-- creation with "ERROR: syntax error at or near FOREACH" (LINE 35: END FOREACH).
-- PL/pgSQL's FOREACH is a LOOP variant — it must close with END LOOP, not
-- END FOREACH. Because this is a parse-time error, the job never executed any
-- of its body even once: soft-deleted clients (deleted_at set 7+ days ago)
-- were never purged from the analytics_v2 big tables or clientes_blu.
--
-- This job was created directly against prod (not tracked in a prior
-- migration), so this migration both fixes and formally registers it.
--
-- Fix verified by running the corrected body inside BEGIN/ROLLBACK against
-- prod before applying — completed with no errors.

select cron.alter_job(
  job_id  := 13,
  command := $cmd$
  DO $cleanup$
  DECLARE
    v_id       uuid;
    v_deleted  int;
    v_big_tables text[] := ARRAY[
      'analytics_v2|dim_inventory',
      'analytics_v2|fato_transacoes',
      'analytics_v2|fato_compras',
      'analytics_v2|dim_clientes',
      'analytics_v2|dim_fornecedores'
    ];
    v_entry    text;
    v_schema   text;
    v_tbl      text;
  BEGIN
    FOR v_id IN
      SELECT client_id FROM public.clientes_blu
      WHERE deleted_at IS NOT NULL
        AND deleted_at < now() - interval '7 days'
    LOOP
      -- Delete big tables in batches of 5000
      FOREACH v_entry IN ARRAY v_big_tables LOOP
        v_schema := split_part(v_entry, '|', 1);
        v_tbl    := split_part(v_entry, '|', 2);
        LOOP
          EXECUTE format(
            'WITH batch AS (SELECT ctid FROM %I.%I WHERE client_id = $1 LIMIT 5000) '
            'DELETE FROM %I.%I WHERE ctid IN (SELECT ctid FROM batch)',
            v_schema, v_tbl, v_schema, v_tbl
          ) USING v_id;
          GET DIAGNOSTICS v_deleted = ROW_COUNT;
          EXIT WHEN v_deleted = 0;
        END LOOP;
      END LOOP;

      -- Hard delete the tenant row (cascade handles remaining FK children)
      DELETE FROM public.clientes_blu WHERE client_id = v_id;
    END LOOP;
  END
  $cleanup$;
  $cmd$
);
