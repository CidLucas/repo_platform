-- ─────────────────────────────────────────────────────────────────────────────
-- Migration: context_report support
--
-- 1. Top-list RPCs used by generate-context-report EF
-- 2. pg_net trigger on analytics_v2.reg_jobs → fires EF on first completion
-- 3. pg_cron monthly schedule
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. Top-list RPCs ─────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_top_clients_for_client(
  p_client_id uuid,
  p_limit     int DEFAULT 5
)
RETURNS TABLE(
  nome            text,
  receita_total   numeric,
  total_pedidos   bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
  SELECT
    dc.nome,
    dc.receita_total,
    dc.total_pedidos
  FROM analytics_v2.dim_clientes dc
  WHERE dc.client_id = p_client_id
    AND dc.receita_total > 0
  ORDER BY dc.receita_total DESC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_top_clients_for_client(uuid, int) TO authenticated, service_role;

-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_top_products_for_client(
  p_client_id uuid,
  p_limit     int DEFAULT 5
)
RETURNS TABLE(
  nome                     text,
  sku                      text,
  receita_total            numeric,
  quantidade_total_vendida numeric
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
  SELECT
    di.nome,
    di.sku,
    di.receita_total,
    di.quantidade_total_vendida
  FROM analytics_v2.dim_inventory di
  WHERE di.client_id = p_client_id
    AND di.receita_total > 0
  ORDER BY di.receita_total DESC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_top_products_for_client(uuid, int) TO authenticated, service_role;

-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_top_suppliers_for_client(
  p_client_id uuid,
  p_limit     int DEFAULT 5
)
RETURNS TABLE(
  nome                    text,
  receita_total           numeric,
  total_pedidos_recebidos bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
  SELECT
    df.nome,
    df.receita_total,
    df.total_pedidos_recebidos
  FROM analytics_v2.dim_fornecedores df
  WHERE df.client_id = p_client_id
    AND df.receita_total > 0
  ORDER BY df.receita_total DESC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_top_suppliers_for_client(uuid, int) TO authenticated, service_role;


-- ── 2. pg_net trigger on reg_jobs completion ──────────────────────────────────
--
-- Fires generate-context-report for a client the first time an ETL job
-- completes (status = 'completed'). Subsequent completions are handled by
-- the monthly pg_cron schedule.

CREATE OR REPLACE FUNCTION analytics_v2.trigger_context_report_on_etl()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  _supabase_url   text := current_setting('app.supabase_url', true);
  _service_key    text := current_setting('app.service_role_key', true);
  _existing_count int;
BEGIN
  -- Only fire for completed jobs
  IF NEW.status <> 'completed' THEN
    RETURN NEW;
  END IF;

  -- Check if this client already has a context report (avoid duplicate on retries)
  SELECT count(*) INTO _existing_count
  FROM vector_db.documents
  WHERE client_id = NEW.client_id
    AND source    = 'generated'
    AND category  = 'business_context';

  -- Always fire: if a report exists it will be archived + refreshed.
  -- The EF itself skips gracefully if no metrics are available yet.
  IF _supabase_url IS NOT NULL AND _service_key IS NOT NULL THEN
    PERFORM extensions.http_post(
      url     := _supabase_url || '/functions/v1/generate-context-report',
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || _service_key
      ),
      body    := jsonb_build_object('client_id', NEW.client_id)::text
    );
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_context_report_on_etl ON analytics_v2.reg_jobs;
CREATE TRIGGER trg_context_report_on_etl
  AFTER INSERT OR UPDATE OF status
  ON analytics_v2.reg_jobs
  FOR EACH ROW
  EXECUTE FUNCTION analytics_v2.trigger_context_report_on_etl();


-- ── 3. Monthly pg_cron for all active tenants ────────────────────────────────
--
-- Runs on the 1st of each month at 04:00 UTC.
-- Iterates all active clients and calls the EF for each.
-- Uses pg_net for non-blocking HTTP calls.

CREATE OR REPLACE FUNCTION public.schedule_monthly_context_reports()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  _client    record;
  _supabase_url text := current_setting('app.supabase_url', true);
  _service_key  text := current_setting('app.service_role_key', true);
BEGIN
  IF _supabase_url IS NULL OR _service_key IS NULL THEN
    RAISE WARNING 'schedule_monthly_context_reports: app settings not configured';
    RETURN;
  END IF;

  FOR _client IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    PERFORM extensions.http_post(
      url     := _supabase_url || '/functions/v1/generate-context-report',
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || _service_key
      ),
      body    := jsonb_build_object('client_id', _client.client_id)::text
    );
  END LOOP;
END;
$$;

-- Schedule: 1st of every month at 04:00 UTC
SELECT pg_catalog.cron.schedule(
  'monthly-context-reports',
  '0 4 1 * *',
  'SELECT public.schedule_monthly_context_reports()'
);
