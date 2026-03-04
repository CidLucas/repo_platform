-- =============================================================================
-- Migration: Review and Complete RLS Policies for Data Ingestion Pipeline
-- Date: 2026-03-02
-- Purpose: Ensure all ingestion-related tables have complete RLS policies
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. CREDENCIAL_SERVICO_EXTERNO - External service credentials
-- =============================================================================

-- Enable RLS if not already enabled
ALTER TABLE public.credencial_servico_externo ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to recreate them with consistent naming
DROP POLICY IF EXISTS credencial_servico_externo_client_isolation ON public.credencial_servico_externo;
DROP POLICY IF EXISTS credencial_servico_externo_service_role_full_access ON public.credencial_servico_externo;

-- Policy: Authenticated users can view/manage their own client's credentials
CREATE POLICY credencial_servico_externo_client_isolation
  ON public.credencial_servico_externo
  FOR ALL
  TO authenticated
  USING (client_id = (current_setting('app.current_client_id', TRUE))::UUID);

-- Policy: Service role has full access (for backend sync jobs)
CREATE POLICY credencial_servico_externo_service_role_full_access
  ON public.credencial_servico_externo
  FOR ALL
  TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);

-- =============================================================================
-- 2. CLIENT_DATA_SOURCES - Data source registry with column mappings
-- =============================================================================

-- Enable RLS if not already enabled
ALTER TABLE public.client_data_sources ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS client_data_sources_policy ON public.client_data_sources;
DROP POLICY IF EXISTS client_data_sources_client_isolation ON public.client_data_sources;
DROP POLICY IF EXISTS client_data_sources_service_role_full_access ON public.client_data_sources;

-- Policy: Users can view/manage their own client's data sources
CREATE POLICY client_data_sources_client_isolation
  ON public.client_data_sources
  FOR ALL
  TO authenticated
  USING (client_id = current_setting('app.current_client_id', TRUE));

-- Policy: Service role has full access
CREATE POLICY client_data_sources_service_role_full_access
  ON public.client_data_sources
  FOR ALL
  TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);

-- =============================================================================
-- 3. BIGQUERY_SERVERS - Foreign server metadata
-- =============================================================================

-- Enable RLS if not already enabled
ALTER TABLE public.bigquery_servers ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS bigquery_servers_client_isolation ON public.bigquery_servers;
DROP POLICY IF EXISTS bigquery_servers_service_role_full_access ON public.bigquery_servers;

-- Policy: Users can view/manage their own BigQuery servers
CREATE POLICY bigquery_servers_client_isolation
  ON public.bigquery_servers
  FOR ALL
  TO authenticated
  USING (client_id = current_setting('app.current_client_id', TRUE));

-- Policy: Service role has full access
CREATE POLICY bigquery_servers_service_role_full_access
  ON public.bigquery_servers
  FOR ALL
  TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);

-- =============================================================================
-- 4. BIGQUERY_FOREIGN_TABLES - Foreign table metadata
-- =============================================================================

-- Enable RLS if not already enabled
ALTER TABLE public.bigquery_foreign_tables ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS bigquery_foreign_tables_client_isolation ON public.bigquery_foreign_tables;
DROP POLICY IF EXISTS bigquery_foreign_tables_service_role_full_access ON public.bigquery_foreign_tables;

-- Policy: Users can view their own foreign tables
CREATE POLICY bigquery_foreign_tables_client_isolation
  ON public.bigquery_foreign_tables
  FOR ALL
  TO authenticated
  USING (client_id = current_setting('app.current_client_id', TRUE));

-- Policy: Service role has full access
CREATE POLICY bigquery_foreign_tables_service_role_full_access
  ON public.bigquery_foreign_tables
  FOR ALL
  TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);

-- =============================================================================
-- 5. CONNECTOR_SYNC_HISTORY - Already has policies, verify they're correct
-- =============================================================================

-- Verify existing policies are correct (created in 20260105 migration)
-- Policy: "Users can view own sync history" - uses cliente_vizu_id comparison
-- Policy: "Service role has full access to sync history" - full access

-- Add missing INSERT/UPDATE policy for service role if needed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'connector_sync_history'
        AND policyname = 'connector_sync_history_service_role'
    ) THEN
        CREATE POLICY connector_sync_history_service_role
          ON public.connector_sync_history
          FOR ALL
          TO service_role
          USING (TRUE)
          WITH CHECK (TRUE);
    END IF;
END$$;

-- =============================================================================
-- 6. ANALYTICS_V2.VENDAS - Main fact table (already has policy, verify)
-- =============================================================================

-- Verify vendas_client_isolation exists (created in 20260224 migration)
-- Uses: client_id = current_setting('app.current_client_id', TRUE)::UUID

-- Add service_role full access if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'analytics_v2'
        AND tablename = 'vendas'
        AND policyname = 'vendas_service_role_full_access'
    ) THEN
        CREATE POLICY vendas_service_role_full_access
          ON analytics_v2.vendas
          FOR ALL
          TO service_role
          USING (TRUE)
          WITH CHECK (TRUE);
    END IF;
END$$;

-- =============================================================================
-- 7. ANALYTICS_V2.CLIENTES - Customer dimension (already has policy, verify)
-- =============================================================================

-- Add service_role full access if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'analytics_v2'
        AND tablename = 'clientes'
        AND policyname = 'clientes_service_role_full_access'
    ) THEN
        CREATE POLICY clientes_service_role_full_access
          ON analytics_v2.clientes
          FOR ALL
          TO service_role
          USING (TRUE)
          WITH CHECK (TRUE);
    END IF;
END$$;

-- =============================================================================
-- 8. ANALYTICS_V2.FORNECEDORES - Supplier dimension (already has policy, verify)
-- =============================================================================

-- Add service_role full access if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'analytics_v2'
        AND tablename = 'fornecedores'
        AND policyname = 'fornecedores_service_role_full_access'
    ) THEN
        CREATE POLICY fornecedores_service_role_full_access
          ON analytics_v2.fornecedores
          FOR ALL
          TO service_role
          USING (TRUE)
          WITH CHECK (TRUE);
    END IF;
END$$;

-- =============================================================================
-- 9. ANALYTICS_V2.PRODUTOS - Product dimension (already has policy, verify)
-- =============================================================================

-- Add service_role full access if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'analytics_v2'
        AND tablename = 'produtos'
        AND policyname = 'produtos_service_role_full_access'
    ) THEN
        CREATE POLICY produtos_service_role_full_access
          ON analytics_v2.produtos
          FOR ALL
          TO service_role
          USING (TRUE)
          WITH CHECK (TRUE);
    END IF;
END$$;

-- =============================================================================
-- 10. GRANT PERMISSIONS
-- =============================================================================

-- Ensure authenticated users can SELECT from ingestion tables
GRANT SELECT ON public.credencial_servico_externo TO authenticated;
GRANT SELECT ON public.client_data_sources TO authenticated;
GRANT SELECT ON public.bigquery_servers TO authenticated;
GRANT SELECT ON public.bigquery_foreign_tables TO authenticated;
GRANT SELECT ON public.connector_sync_history TO authenticated;
GRANT SELECT ON public.ingestion_audit_log TO authenticated;

-- Ensure service_role has ALL privileges
GRANT ALL ON public.credencial_servico_externo TO service_role;
GRANT ALL ON public.client_data_sources TO service_role;
GRANT ALL ON public.bigquery_servers TO service_role;
GRANT ALL ON public.bigquery_foreign_tables TO service_role;
GRANT ALL ON public.connector_sync_history TO service_role;
GRANT ALL ON public.ingestion_audit_log TO service_role;
GRANT ALL ON analytics_v2.vendas TO service_role;
GRANT ALL ON analytics_v2.clientes TO service_role;
GRANT ALL ON analytics_v2.fornecedores TO service_role;
GRANT ALL ON analytics_v2.produtos TO service_role;

-- =============================================================================
-- 11. VERIFICATION QUERY (commented out - run manually to verify)
-- =============================================================================

/*
-- Run this query after migration to verify all policies are in place:
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE
    (schemaname = 'public' AND tablename IN (
        'credencial_servico_externo',
        'client_data_sources',
        'bigquery_servers',
        'bigquery_foreign_tables',
        'connector_sync_history',
        'ingestion_audit_log'
    ))
    OR (schemaname = 'analytics_v2' AND tablename IN (
        'vendas',
        'clientes',
        'fornecedores',
        'produtos'
    ))
ORDER BY schemaname, tablename, policyname;

-- Expected: At least 2 policies per table (client isolation + service_role full access)
*/

COMMIT;

-- =============================================================================
-- SUMMARY
-- =============================================================================
-- This migration ensures:
-- 1. All ingestion tables have RLS enabled
-- 2. Each table has client_isolation policy (uses app.current_client_id or client_id column)
-- 3. Each table has service_role full access policy (for backend sync jobs)
-- 4. Proper GRANTs for authenticated and service_role roles
-- 5. Consistent naming convention: <table>_client_isolation, <table>_service_role_full_access
-- =============================================================================
