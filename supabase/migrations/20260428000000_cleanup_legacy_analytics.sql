-- =============================================================================
-- Migration: Cleanup — Drop all legacy analytics_gold_* structures
-- Date: 2026-04-28
-- Purpose: Remove conflicting legacy analytics tables/views before baseline
-- Note: This migration runs BEFORE the baseline phase migrations
-- =============================================================================

BEGIN;

-- Drop all legacy analytics_gold_* tables (created by earlier migrations, replaced by analytics_v2)
DROP TABLE IF EXISTS public.analytics_gold_orders CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_customers CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_products CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_customer_products CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_last_orders CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_regional CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_time_series CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_sales CASCADE;
DROP TABLE IF EXISTS public.analytics_silver CASCADE;

-- Drop any legacy views
DROP VIEW IF EXISTS public.view_analytics_sales CASCADE;
DROP VIEW IF EXISTS public.view_analytics_customers CASCADE;
DROP VIEW IF EXISTS public.view_analytics_suppliers CASCADE;

COMMIT;
