-- ─────────────────────────────────────────────────────────────────────────────
-- FASE 1 · Cascade delete cleanup
--
-- Fix 1: bigquery_foreign_tables.credential_id → credencial_servico_externo
--   NO ACTION → CASCADE: deleting a credential removes its BQ table metadata rows.
--
-- Fix 2: standalone_agent_sessions.agent_catalog_id → agent_catalog
--   RESTRICT → SET NULL: sessions are deleted with the client (via client_id CASCADE),
--   agents remain in catalog. RESTRICT was blocking catalog cleanup; SET NULL is safe.
--
-- Fix 3: FDW server cleanup trigger on bigquery_servers DELETE
--   When a bigquery_servers row is removed (cascades from clientes_blu.client_id),
--   the actual PostgreSQL FDW SERVER object must also be dropped or subsequent
--   CREATE SERVER calls will fail with "already exists".
-- ─────────────────────────────────────────────────────────────────────────────

-- Fix 1
ALTER TABLE public.bigquery_foreign_tables
  DROP CONSTRAINT bigquery_foreign_tables_credential_id_fkey,
  ADD CONSTRAINT bigquery_foreign_tables_credential_id_fkey
    FOREIGN KEY (credential_id)
    REFERENCES public.credencial_servico_externo(id)
    ON DELETE CASCADE;

-- Fix 2
ALTER TABLE public.standalone_agent_sessions
  DROP CONSTRAINT standalone_agent_sessions_agent_catalog_id_fkey,
  ADD CONSTRAINT standalone_agent_sessions_agent_catalog_id_fkey
    FOREIGN KEY (agent_catalog_id)
    REFERENCES public.agent_catalog(id)
    ON DELETE SET NULL;

-- Fix 3: trigger function
CREATE OR REPLACE FUNCTION public.drop_bigquery_fdw_server()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Drops the FDW server and all dependent foreign tables in the fdw schema.
  -- EXECUTE is required because server name is dynamic.
  EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', OLD.server_name);
  RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_drop_bigquery_fdw_server ON public.bigquery_servers;
CREATE TRIGGER trg_drop_bigquery_fdw_server
  BEFORE DELETE ON public.bigquery_servers
  FOR EACH ROW EXECUTE FUNCTION public.drop_bigquery_fdw_server();
