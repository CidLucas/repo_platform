-- Migration: dashboard activity RPCs (recent activity, pendências, agent runs)
-- Date: 2026-04-23
-- Phase: Dashboard mocks → live data, Phase 1
--
-- Adds three SECURITY INVOKER RPCs in the public schema, scoped via
-- public.get_my_client_id():
--   * get_recent_activity(limit)  — UNION feed across ingestion / agents / RFQ / uploads
--   * get_pendencias()            — UNION of action items (RFQ pending, sync errors)
--   * get_agent_runs_today()      — count of standalone_agent_sessions today + per-agent

-- ── 1. get_recent_activity ───────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_recent_activity(
  p_limit int DEFAULT 10
)
RETURNS TABLE (
  kind         text,
  title        text,
  subtitle     text,
  occurred_at  timestamptz,
  severity     text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public
AS $$
  WITH me AS (SELECT public.get_my_client_id() AS client_id_text),
  ingestion AS (
    SELECT
      'ingestion'::text                                       AS kind,
      ('Sincronização ' || COALESCE(csh.resource_type, 'dados'))::text AS title,
      CASE csh.status
        WHEN 'completed' THEN
          (COALESCE(csh.records_processed, 0)::text || ' registros processados')
        ELSE COALESCE(csh.error_message, 'Falha na sincronização')
      END                                                     AS subtitle,
      COALESCE(csh.sync_completed_at, csh.sync_started_at)    AS occurred_at,
      CASE csh.status WHEN 'completed' THEN 'info' ELSE 'error' END AS severity
    FROM public.connector_sync_history csh
    CROSS JOIN me
    WHERE csh.status IN ('completed', 'failed')
      AND COALESCE(csh.sync_completed_at, csh.sync_started_at) >= now() - interval '7 days'
      AND csh.client_id::text = me.client_id_text
  ),
  agent_runs AS (
    SELECT
      'agent_session'::text                                   AS kind,
      ('Sessão ' || COALESCE(ac.name, 'agente'))::text        AS title,
      ('Status: ' || COALESCE(sas.config_status, 'ativo'))::text AS subtitle,
      sas.created_at                                          AS occurred_at,
      'info'::text                                            AS severity
    FROM public.standalone_agent_sessions sas
    LEFT JOIN public.agent_catalog ac ON ac.id = sas.agent_catalog_id
    CROSS JOIN me
    WHERE sas.created_at >= now() - interval '7 days'
      AND sas.client_id::text = me.client_id_text
  ),
  rfqs AS (
    SELECT
      'rfq'::text                                             AS kind,
      ('RFQ ' || rr.status)::text                             AS title,
      ('Fornecedor: ' || COALESCE(sr.name, 'desconhecido'))::text AS subtitle,
      COALESCE(rr.sent_at, rr.created_at)                     AS occurred_at,
      CASE rr.status
        WHEN 'expired'   THEN 'warning'
        WHEN 'cancelled' THEN 'warning'
        ELSE 'info'
      END                                                     AS severity
    FROM public.rfq_requests rr
    LEFT JOIN public.supplier_roster sr ON sr.id = rr.supplier_id
    CROSS JOIN me
    WHERE COALESCE(rr.sent_at, rr.created_at) >= now() - interval '7 days'
      AND rr.client_id::text = me.client_id_text
  ),
  uploads AS (
    SELECT
      'upload'::text                                          AS kind,
      ufm.file_name::text                                     AS title,
      (COALESCE(ufm.records_imported, 0)::text || ' registros importados')::text AS subtitle,
      COALESCE(ufm.processed_at, ufm.uploaded_at)             AS occurred_at,
      CASE ufm.status WHEN 'failed' THEN 'error' ELSE 'info' END AS severity
    FROM public.uploaded_files_metadata ufm
    CROSS JOIN me
    WHERE COALESCE(ufm.processed_at, ufm.uploaded_at) >= now() - interval '7 days'
      AND ufm.cliente_vizu_id::text = me.client_id_text
  )
  SELECT * FROM (
    SELECT * FROM ingestion
    UNION ALL SELECT * FROM agent_runs
    UNION ALL SELECT * FROM rfqs
    UNION ALL SELECT * FROM uploads
  ) feed
  ORDER BY occurred_at DESC NULLS LAST
  LIMIT GREATEST(p_limit, 1);
$$;

GRANT EXECUTE ON FUNCTION public.get_recent_activity(int) TO authenticated;

-- ── 2. get_pendencias ────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_pendencias()
RETURNS TABLE (
  kind          text,
  title         text,
  severity      text,
  occurred_at   timestamptz,
  target_route  text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public
AS $$
  WITH me AS (SELECT public.get_my_client_id() AS client_id_text),
  rfq_pending AS (
    SELECT
      'rfq_pending'::text                                     AS kind,
      ('RFQ aguardando envio (' || COALESCE(sr.name, '—') || ')')::text AS title,
      'warning'::text                                         AS severity,
      rr.created_at                                           AS occurred_at,
      '/dashboard/rfq'::text                                  AS target_route
    FROM public.rfq_requests rr
    LEFT JOIN public.supplier_roster sr ON sr.id = rr.supplier_id
    CROSS JOIN me
    WHERE rr.status = 'pending'
      AND rr.client_id::text = me.client_id_text
  ),
  sync_errors AS (
    SELECT
      'connector_error'::text                                 AS kind,
      ('Erro de sincronização — ' || COALESCE(csh.resource_type, 'dados'))::text AS title,
      'error'::text                                           AS severity,
      COALESCE(csh.sync_completed_at, csh.sync_started_at)    AS occurred_at,
      '/dashboard/admin/connectors'::text                     AS target_route
    FROM public.connector_sync_history csh
    CROSS JOIN me
    WHERE csh.status = 'failed'
      AND COALESCE(csh.sync_completed_at, csh.sync_started_at) >= now() - interval '30 days'
      AND csh.client_id::text = me.client_id_text
  ),
  data_source_issues AS (
    SELECT
      'data_source_issue'::text                               AS kind,
      ('Fonte de dados ' || cds.sync_status || ' — ' || cds.resource_type)::text AS title,
      CASE cds.sync_status WHEN 'error' THEN 'error' ELSE 'warning' END AS severity,
      cds.updated_at                                          AS occurred_at,
      '/dashboard/admin/connectors'::text                     AS target_route
    FROM public.client_data_sources cds
    CROSS JOIN me
    WHERE cds.sync_status IN ('pending', 'error')
      AND cds.client_id::text = me.client_id_text
  )
  SELECT * FROM (
    SELECT * FROM rfq_pending
    UNION ALL SELECT * FROM sync_errors
    UNION ALL SELECT * FROM data_source_issues
  ) p
  ORDER BY
    CASE severity WHEN 'error' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
    occurred_at DESC NULLS LAST;
$$;

GRANT EXECUTE ON FUNCTION public.get_pendencias() TO authenticated;

-- ── 3. get_agent_runs_today ──────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_agent_runs_today()
RETURNS TABLE (
  total     bigint,
  by_agent  jsonb
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public
AS $$
  WITH me AS (SELECT public.get_my_client_id() AS client_id_text),
  today_runs AS (
    SELECT
      COALESCE(ac.slug, ac.name, 'unknown') AS agent_key
    FROM public.standalone_agent_sessions sas
    LEFT JOIN public.agent_catalog ac ON ac.id = sas.agent_catalog_id
    CROSS JOIN me
    WHERE sas.client_id::text = me.client_id_text
      AND sas.created_at >= date_trunc('day', (now() AT TIME ZONE 'America/Sao_Paulo'))
                            AT TIME ZONE 'America/Sao_Paulo'
  ),
  by_agent_agg AS (
    SELECT agent_key, COUNT(*)::bigint AS cnt
    FROM today_runs
    GROUP BY agent_key
  )
  SELECT
    COALESCE((SELECT SUM(cnt) FROM by_agent_agg), 0)::bigint AS total,
    COALESCE(
      (SELECT jsonb_object_agg(agent_key, cnt) FROM by_agent_agg),
      '{}'::jsonb
    )                                                        AS by_agent;
$$;

GRANT EXECUTE ON FUNCTION public.get_agent_runs_today() TO authenticated;

COMMENT ON FUNCTION public.get_recent_activity(int) IS
  'Dashboard HomePage Recent Activity feed. UNION across connector_sync_history, standalone_agent_sessions, rfq_requests, uploaded_files_metadata. RLS-scoped via public.get_my_client_id().';
COMMENT ON FUNCTION public.get_pendencias() IS
  'Dashboard HomePage Pendências card. RLS-scoped via public.get_my_client_id().';
COMMENT ON FUNCTION public.get_agent_runs_today() IS
  'Dashboard HomePage AI Tasks tile. Counts standalone_agent_sessions created today (America/Sao_Paulo). RLS-scoped.';
