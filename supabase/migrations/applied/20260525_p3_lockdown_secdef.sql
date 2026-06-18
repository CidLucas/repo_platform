-- 20260525_p3_lockdown_secdef_pub.sql
-- P3: Lockdown SECURITY DEFINER functions exposed to PUBLIC/anon/authenticated.
-- Strategy: REVOKE EXECUTE on dangerous SECDEF functions, restrict to service_role.
-- Functions that legitimately need 'authenticated' access (because they use
-- auth.uid()/get_my_client_id() internally) are left untouched: ensure_tenant_row,
-- enqueue_routine_for_me, get_my_client_id, get_my_* family.

BEGIN;

-- ============================================================================
-- 1. Vault / OAuth — backend-only (service_role)
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.get_platform_google_oauth_config()
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_user_oauth_tokens(uuid, text, text)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.upsert_user_oauth_tokens(uuid, text, text, text, text, text, timestamptz, text[], jsonb, boolean)
  FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 2. Tenant context impersonation — backend-only
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.set_current_client_id(uuid)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.set_current_cliente_id(uuid)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.set_current_customer_id(uuid)
  FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 3. Tenant destruction — backend-only
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.offboard_client(uuid, integer)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.offboard_client_batch(uuid, text, text, integer)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.soft_delete_client(uuid)
  FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 4. Knowledge / onboarding bootstrap — accepts arbitrary client_id, backend-only
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.bootstrap_knowledge_from_onboarding(uuid)
  FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 5. Routine dispatch — backend-only
-- (frontend must use public.enqueue_routine_for_me(routine_id) which uses
--  get_my_client_id() internally and is kept accessible)
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.enqueue_routine(uuid, text, text, jsonb, integer)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.enqueue_custom_routine(uuid, text, jsonb, integer)
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.enqueue_monthly_close()
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.schedule_monthly_context_reports()
  FROM PUBLIC, anon, authenticated;
-- fire_event_for_client and dispatch_routine_event already restricted; reinforce.
REVOKE EXECUTE ON FUNCTION public.dispatch_routine_event(text, uuid, jsonb)
  FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.fire_event_for_client(text, uuid, jsonb)
  FROM PUBLIC;

-- ============================================================================
-- 6. BigQuery FDW — create/drop/foreign_table HAVE internal guard against
--    cross-tenant access (check p_client_id == get_my_client_id()), so they
--    stay accessible to authenticated. BUT create_bigquery_foreign_table_from_schema
--    has NO guard and was called only by edge function (service_role) — revoke.
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.create_bigquery_foreign_table_from_schema(text, jsonb)
  FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 7. exec_sql — already guarded by session_user check, but tighten grants
-- ============================================================================
REVOKE EXECUTE ON FUNCTION public.exec_sql(text)
  FROM PUBLIC;

-- ============================================================================
-- 8. analytics_v2 — every function with PUBLIC grant becomes service_role-only
-- (these are ETL/aggregation primitives called by cron + backend; authenticated
--  users should consume them ONLY via public.* wrapper functions which already
--  scope by get_my_client_id())
-- ============================================================================
REVOKE EXECUTE ON FUNCTION analytics_v2._period_range(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.atualizar_agregados(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.atualizar_dim_clientes(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.atualizar_dim_fornecedores(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.atualizar_dim_inventory(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.enqueue_incremental_syncs() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.enqueue_polp_sync() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_admin_indicators(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_annual_metrics_for_client(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_commercial_indicators(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_commercial_revenue_by_channel(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_commercial_top_clients(text, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_context_metrics_for_client(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_context_metrics_for_client(uuid, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION analytics_v2.get_context_metrics_for_client(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.get_context_metrics_for_client(uuid, text) TO service_role;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_dim_totals_for_client(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_finance_indicators(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_indicators_for_client(uuid, text, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_indicators_for_client(uuid, text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_inventory_indicators(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_kpi_mtd_comparison(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_kpi_mtd_comparison() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_marketing_indicators(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.get_supply_indicators(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION analytics_v2.on_etl_job_completed() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.process_pending_csv_jobs() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.process_pending_etl_jobs() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.run_etl_job(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.sync_polp_transactions(uuid, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.sync_polp_transactions(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION analytics_v2.trigger_context_report_on_etl() FROM PUBLIC;

-- ============================================================================
-- 9. Catalogs: cnpj_enrichments + canonical_columns — read-only for clients
-- ============================================================================
REVOKE INSERT, UPDATE, DELETE ON public.cnpj_enrichments FROM PUBLIC, anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.canonical_columns FROM PUBLIC, anon, authenticated;

COMMIT;
