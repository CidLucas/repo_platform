-- Migration: soft delete pattern for clientes_blu
-- Adds deleted_at column, view active_clientes_blu, soft_delete_client() function,
-- and pg_cron nightly cleanup job.

-- 1. Add deleted_at column (nullable = not deleted)
ALTER TABLE public.clientes_blu
  ADD COLUMN IF NOT EXISTS deleted_at timestamptz DEFAULT NULL;

-- 2. Index for nightly cleanup job (only hits rows with deleted_at set)
CREATE INDEX IF NOT EXISTS idx_clientes_blu_deleted_at
  ON public.clientes_blu(deleted_at)
  WHERE deleted_at IS NOT NULL;

-- 3. View: active tenants (what the app should query)
CREATE OR REPLACE VIEW public.active_clientes_blu AS
  SELECT * FROM public.clientes_blu WHERE deleted_at IS NULL;

COMMENT ON VIEW public.active_clientes_blu IS
  'Active tenants only. Use instead of clientes_blu in application queries.';

-- 4. Soft delete function (replaces hard DELETE for normal offboarding)
CREATE OR REPLACE FUNCTION public.soft_delete_client(
    p_client_id uuid
)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE public.clientes_blu
     SET deleted_at = now()
   WHERE client_id = p_client_id
     AND deleted_at IS NULL;  -- idempotent
$$;

COMMENT ON FUNCTION public.soft_delete_client(uuid) IS
  'Mark a client as deleted (soft delete). Data is retained for 7 days '
  'then cleaned up by the nightly pg_cron job offboard_cleanup_nightly.';

-- 5. Nightly cleanup via pg_cron (runs at 03:00 UTC)
-- Deletes data for clients soft-deleted more than 7 days ago, in batches.
-- Requires pg_cron extension (available on Supabase).
SELECT cron.schedule(
  'offboard_cleanup_nightly',
  '0 3 * * *',
  $$
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
      END FOREACH;

      -- Hard delete the tenant row (cascade handles remaining FK children)
      DELETE FROM public.clientes_blu WHERE client_id = v_id;
    END LOOP;
  END
  $cleanup$;
  $$
);