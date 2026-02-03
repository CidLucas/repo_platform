-- =============================================================================
-- Migration: Enable RLS on analytics_v2 tables
-- Date: 2026-01-28
-- Purpose: Add Row Level Security to analytics_v2 star schema tables
-- Status: APPLIED via MCP
-- =============================================================================

-- =============================================================================
-- 1. ENABLE ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE analytics_v2.fact_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_customer ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_supplier ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_product ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 2. FORCE RLS (even for table owners)
-- =============================================================================

ALTER TABLE analytics_v2.fact_sales FORCE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_customer FORCE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_supplier FORCE ROW LEVEL SECURITY;
ALTER TABLE analytics_v2.dim_product FORCE ROW LEVEL SECURITY;

-- =============================================================================
-- 3. CREATE RLS POLICIES
-- =============================================================================

-- Policy for fact_sales: clients can only access their own sales data
CREATE POLICY fact_sales_client_isolation ON analytics_v2.fact_sales
    FOR ALL
    USING (
        client_id = COALESCE(
            current_setting('app.current_cliente_id', true),
            '00000000-0000-0000-0000-000000000000'
        )
    );

-- Policy for dim_customer: clients can only access their own customers
CREATE POLICY dim_customer_client_isolation ON analytics_v2.dim_customer
    FOR ALL
    USING (
        client_id = COALESCE(
            current_setting('app.current_cliente_id', true),
            '00000000-0000-0000-0000-000000000000'
        )
    );

-- Policy for dim_supplier: clients can only access their own suppliers
CREATE POLICY dim_supplier_client_isolation ON analytics_v2.dim_supplier
    FOR ALL
    USING (
        client_id = COALESCE(
            current_setting('app.current_cliente_id', true),
            '00000000-0000-0000-0000-000000000000'
        )
    );

-- Policy for dim_product: clients can only access their own products
CREATE POLICY dim_product_client_isolation ON analytics_v2.dim_product
    FOR ALL
    USING (
        client_id = COALESCE(
            current_setting('app.current_cliente_id', true),
            '00000000-0000-0000-0000-000000000000'
        )
    );

-- =============================================================================
-- 4. GRANT PERMISSIONS TO AUTHENTICATED USERS
-- =============================================================================

GRANT SELECT ON analytics_v2.fact_sales TO authenticated;
GRANT SELECT ON analytics_v2.dim_customer TO authenticated;
GRANT SELECT ON analytics_v2.dim_supplier TO authenticated;
GRANT SELECT ON analytics_v2.dim_product TO authenticated;

GRANT ALL ON analytics_v2.fact_sales TO service_role;
GRANT ALL ON analytics_v2.dim_customer TO service_role;
GRANT ALL ON analytics_v2.dim_supplier TO service_role;
GRANT ALL ON analytics_v2.dim_product TO service_role;
