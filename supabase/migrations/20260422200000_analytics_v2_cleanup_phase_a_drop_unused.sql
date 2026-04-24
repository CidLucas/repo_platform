-- Analytics V2 Cleanup — Phase A
-- Snapshot soon-to-be-dropped tables into analytics_v2_legacy, then drop:
--   - Out-of-scope tables: dim_resources, dim_categoria, fact_reservations,
--     fact_availability, fcx_tax_config
--   - Unused views: v_clientes_30d, v_fornecedores_30d, v_produtos_30d,
--     vw_contas_aging, vw_dre_mensal, vw_fluxo_caixa_mensal
--   - ERP/reservation functions that no service or UI still imports
--
-- Reference: docs/plans/2026-04-22-analytics-v2-minimal-schema-cleanup.md (Phase A, C)

BEGIN;

-- ── 1. Snapshot schema ────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS analytics_v2_legacy;
COMMENT ON SCHEMA analytics_v2_legacy IS
  'Frozen snapshots of analytics_v2 tables dropped during the Apr 2026 minimal-schema cleanup. Read-only fallback.';

-- Snapshot via CREATE TABLE AS to preserve data; indexes/constraints intentionally not copied.
CREATE TABLE analytics_v2_legacy.dim_resources       AS TABLE analytics_v2.dim_resources;
CREATE TABLE analytics_v2_legacy.dim_categoria       AS TABLE analytics_v2.dim_categoria;
CREATE TABLE analytics_v2_legacy.fact_reservations   AS TABLE analytics_v2.fact_reservations;
CREATE TABLE analytics_v2_legacy.fact_availability   AS TABLE analytics_v2.fact_availability;
CREATE TABLE analytics_v2_legacy.fcx_tax_config      AS TABLE analytics_v2.fcx_tax_config;

-- Tenant isolation on legacy schema (deny by default; only service role can read).
REVOKE ALL ON ALL TABLES IN SCHEMA analytics_v2_legacy FROM anon, authenticated;
GRANT  SELECT ON ALL TABLES IN SCHEMA analytics_v2_legacy TO service_role;

-- ── 2. Drop unused views ──────────────────────────────────────────────
DROP VIEW IF EXISTS analytics_v2.v_clientes_30d        CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_fornecedores_30d    CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_produtos_30d        CASCADE;
DROP VIEW IF EXISTS analytics_v2.vw_contas_aging       CASCADE;
DROP VIEW IF EXISTS analytics_v2.vw_dre_mensal         CASCADE;
DROP VIEW IF EXISTS analytics_v2.vw_fluxo_caixa_mensal CASCADE;

-- ── 3. Drop unused functions ─────────────────────────────────────────
-- ERP helpers referenced only by the unused apps/vizu_dashboard/src/services/erpService.ts
DROP FUNCTION IF EXISTS analytics_v2.erp_ajustar_estoque        CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_atualizar_cliente      CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_atualizar_job          CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_busca                  CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_buscar_cliente         CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_buscar_fornecedor      CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_criar_cliente          CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_criar_fornecedor       CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_criar_job              CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_criar_ordem_compra     CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_criar_pedido           CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_criar_produto          CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.erp_receber_ordem_compra   CASCADE;
DROP FUNCTION IF EXISTS public.erp_criar_produto                CASCADE;

-- Reservation sync (hospitality Option B, not in v1 UI)
DROP FUNCTION IF EXISTS analytics_v2.sync_reservation_availability CASCADE;

-- Enrich function referenced dim_categoria + wide fato columns we are about to drop;
-- the multi-table ETL (phase D) replaces this flow entirely.
DROP FUNCTION IF EXISTS analytics_v2.enrich_fato_transacoes_from_source CASCADE;

-- ── 4. Drop unused tables ─────────────────────────────────────────────
DROP TABLE IF EXISTS analytics_v2.fact_availability   CASCADE;
DROP TABLE IF EXISTS analytics_v2.fact_reservations   CASCADE;
DROP TABLE IF EXISTS analytics_v2.dim_resources       CASCADE;
DROP TABLE IF EXISTS analytics_v2.dim_categoria       CASCADE;
DROP TABLE IF EXISTS analytics_v2.fcx_tax_config      CASCADE;

COMMIT;
