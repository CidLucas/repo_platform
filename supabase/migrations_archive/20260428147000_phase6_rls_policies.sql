-- =============================================================================
-- Migration: Phase 6 — RLS policies baseline
-- Date: 2026-04-28
-- Purpose: Enable row-level security and set up tenant isolation policies
-- =============================================================================

BEGIN;

-- ============================================================================
-- Enable RLS on all tenant-scoped tables
-- ============================================================================

ALTER TABLE public.clientes_blu             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_data_sources      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_tokens       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_configs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_settings        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nps_responses            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_requests        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_insights          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_runs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_schedules         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_enabled_agents    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_routines          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.standalone_agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_files_metadata  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.frontend_events          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_dimension_kpis    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversa                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.fato_transacoes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_clientes       ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_fornecedores   ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_inventory      ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.reg_jobs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_db.documents             ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_db.document_chunks       ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- clientes_blu: user sees/edits only their own row
-- ============================================================================

CREATE POLICY "own row" ON public.clientes_blu FOR ALL TO authenticated
  USING (external_user_id = auth.uid()::text)
  WITH CHECK (external_user_id = auth.uid()::text);

-- ============================================================================
-- Generic client_id pattern for all tenant-scoped tables
-- ============================================================================

CREATE POLICY "own client" ON public.client_data_sources FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id()::text);

CREATE POLICY "own client" ON public.integration_tokens FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.integration_configs FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.calendar_settings FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.nps_responses FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.approval_requests FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.audit_log FOR SELECT TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.client_insights FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.report_runs FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.report_schedules FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.client_enabled_agents FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.client_routines FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.standalone_agent_sessions FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.uploaded_files_metadata FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.frontend_events FOR INSERT TO authenticated
  WITH CHECK (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.client_dimension_kpis FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.conversa FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON public.messages FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

-- ============================================================================
-- analytics_v2 tables
-- ============================================================================

CREATE POLICY "own client" ON analytics_v2.fato_transacoes FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON analytics_v2.dim_clientes FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON analytics_v2.dim_fornecedores FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON analytics_v2.dim_inventory FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON analytics_v2.reg_jobs FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

-- ============================================================================
-- vector_db tables
-- ============================================================================

CREATE POLICY "own client" ON vector_db.documents FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE POLICY "own client" ON vector_db.document_chunks FOR SELECT TO authenticated
  USING (client_id = public.get_my_client_id());

-- ============================================================================
-- Global read-only tables (not tenant-scoped)
-- ============================================================================

ALTER TABLE public.agent_catalog  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kpi_catalog    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "read all" ON public.agent_catalog FOR SELECT TO authenticated
  USING (is_active = true);

CREATE POLICY "read all" ON public.kpi_catalog FOR SELECT TO authenticated
  USING (true);

COMMIT;
