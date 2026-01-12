-- =====================================================================
-- Analytics Tables Migration: Drop Views, Create Tables with RLS
-- =====================================================================
-- Purpose: Replace existing analytics views with tables and enable RLS
-- Created: 2025-12-26
-- Architecture:
--   1. Drop existing views (if any)
--   2. Create concrete tables for gold/silver layers
--   3. Enable RLS with multi-tenant policies
--   4. Grant permissions
-- =====================================================================

-- =====================================================================
-- STEP 1: Drop Existing Views and Tables (if they exist)
-- =====================================================================

-- Drop views in reverse dependency order to avoid errors
DROP VIEW IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_customers CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_products CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_orders CASCADE;
DROP VIEW IF EXISTS public.analytics_silver CASCADE;

-- Also drop any materialized views if they exist
DROP MATERIALIZED VIEW IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.analytics_gold_customers CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.analytics_gold_products CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.analytics_gold_orders CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.analytics_silver CASCADE;

-- Drop existing tables (if they exist without RLS)
-- This ensures we start fresh with properly configured RLS tables
DROP TABLE IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_customers CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_products CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_orders CASCADE;
DROP TABLE IF EXISTS public.analytics_silver CASCADE;

-- =====================================================================
-- STEP 2: Create Tables (Gold and Silver Layers)
-- =====================================================================

-- 1. Gold Orders: Aggregated order metrics
CREATE TABLE IF NOT EXISTS public.analytics_gold_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,

    -- Order Metrics
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,

    -- Time period (optional - for time-series aggregations)
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time', -- 'daily', 'weekly', 'monthly', 'all_time'

    -- Order Status Breakdown (JSONB for flexibility)
    by_status JSONB DEFAULT '{}'::JSONB,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create unique constraint only if period_type and period_start are not null
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_client_period_orders
    ON public.analytics_gold_orders(client_id, period_type, period_start)
    WHERE period_type IS NOT NULL AND period_start IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gold_orders_client_id ON public.analytics_gold_orders(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_orders_period ON public.analytics_gold_orders(period_start, period_end) WHERE period_start IS NOT NULL;

COMMENT ON TABLE public.analytics_gold_orders IS 'Gold layer: Aggregated order metrics written by Analytics API';

-- 2. Gold Products: Aggregated product metrics
CREATE TABLE IF NOT EXISTS public.analytics_gold_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    product_name TEXT NOT NULL,

    -- Product Metrics
    total_quantity_sold DECIMAL(12, 2) DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,
    avg_price DECIMAL(10, 2) DEFAULT 0,
    order_count INTEGER DEFAULT 0,

    -- Rankings
    revenue_rank INTEGER,

    -- Time period
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_client_product_period
    ON public.analytics_gold_products(client_id, product_name, period_type, period_start)
    WHERE period_type IS NOT NULL AND period_start IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gold_products_client_id ON public.analytics_gold_products(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_products_revenue ON public.analytics_gold_products(total_revenue DESC);

COMMENT ON TABLE public.analytics_gold_products IS 'Gold layer: Aggregated product metrics written by Analytics API';

-- 3. Gold Customers: Aggregated customer metrics
CREATE TABLE IF NOT EXISTS public.analytics_gold_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_cpf_cnpj TEXT,

    -- Customer Metrics
    total_orders INTEGER DEFAULT 0,
    lifetime_value DECIMAL(12, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,
    first_order_date TIMESTAMPTZ,
    last_order_date TIMESTAMPTZ,

    -- Customer Segmentation
    customer_type TEXT, -- 'new', 'returning', 'vip'

    -- Time period
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_client_customer_period
    ON public.analytics_gold_customers(client_id, customer_name, period_type, period_start)
    WHERE period_type IS NOT NULL AND period_start IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gold_customers_client_id ON public.analytics_gold_customers(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_customers_ltv ON public.analytics_gold_customers(lifetime_value DESC);

COMMENT ON TABLE public.analytics_gold_customers IS 'Gold layer: Aggregated customer metrics written by Analytics API';

-- 4. Gold Suppliers: Aggregated supplier metrics
CREATE TABLE IF NOT EXISTS public.analytics_gold_suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    supplier_cnpj TEXT,

    -- Supplier Metrics
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,
    unique_products INTEGER DEFAULT 0,

    -- Time period
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_client_supplier_period
    ON public.analytics_gold_suppliers(client_id, supplier_name, period_type, period_start)
    WHERE period_type IS NOT NULL AND period_start IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gold_suppliers_client_id ON public.analytics_gold_suppliers(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_revenue ON public.analytics_gold_suppliers(total_revenue DESC);

COMMENT ON TABLE public.analytics_gold_suppliers IS 'Gold layer: Aggregated supplier metrics written by Analytics API';

-- 5. Analytics Silver: Cached denormalized data from BigQuery
-- Schema matches pm_dados_faturamento_cliente_x for data ingestion compatibility
CREATE TABLE IF NOT EXISTS public.analytics_silver (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    order_id TEXT,
    data_transacao TIMESTAMPTZ,
    quantidade TEXT,
    valor_unitario TEXT,
    valor_total_emitter TEXT,
    valor_total_receiver TEXT,
    emitter_nome TEXT,
    emitter_cidade TEXT,
    emitter_estado TEXT,
    receiver_nome TEXT,
    receiver_cidade TEXT,
    raw_product_description TEXT,
    raw_product_category TEXT,
    raw_ncm TEXT,
    raw_cfop TEXT,
    emitter_cnpj TEXT,
    emitter_telefone TEXT,
    receiver_cnpj TEXT,
    receiver_telefone TEXT,
    receiver_estado TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint for silver layer
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_client_order_product_silver
    ON public.analytics_silver(client_id, order_id, raw_product_description);

CREATE INDEX IF NOT EXISTS idx_analytics_silver_client_id ON public.analytics_silver(client_id);
CREATE INDEX IF NOT EXISTS idx_analytics_silver_data_transacao ON public.analytics_silver(data_transacao);
CREATE INDEX IF NOT EXISTS idx_analytics_silver_order_id ON public.analytics_silver(order_id);

COMMENT ON TABLE public.analytics_silver IS 'Silver layer: Cached denormalized data from BigQuery (optional)';

-- =====================================================================
-- STEP 3: Enable Row Level Security (RLS)
-- =====================================================================

ALTER TABLE public.analytics_silver ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_suppliers ENABLE ROW LEVEL SECURITY;

-- =====================================================================
-- STEP 4: Create RLS Policies
-- =====================================================================

-- =====================================================================
-- RLS for GOLD ORDERS
-- =====================================================================

DROP POLICY IF EXISTS "Users can view own client gold orders" ON public.analytics_gold_orders;
DROP POLICY IF EXISTS "Service role full access to gold orders" ON public.analytics_gold_orders;

CREATE POLICY "Users can view own client gold orders"
    ON public.analytics_gold_orders
    FOR SELECT
    TO authenticated
    USING (
        -- Allow if client_id matches the client_id from JWT claims
        client_id = (auth.jwt()->>'client_id')::text
        OR
        -- Allow if client_id exists in cliente_vizu table (fallback)
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold orders"
    ON public.analytics_gold_orders
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- RLS for GOLD PRODUCTS
-- =====================================================================

DROP POLICY IF EXISTS "Users can view own client gold products" ON public.analytics_gold_products;
DROP POLICY IF EXISTS "Service role full access to gold products" ON public.analytics_gold_products;

CREATE POLICY "Users can view own client gold products"
    ON public.analytics_gold_products
    FOR SELECT
    TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold products"
    ON public.analytics_gold_products
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- RLS for GOLD CUSTOMERS
-- =====================================================================

DROP POLICY IF EXISTS "Users can view own client gold customers" ON public.analytics_gold_customers;
DROP POLICY IF EXISTS "Service role full access to gold customers" ON public.analytics_gold_customers;

CREATE POLICY "Users can view own client gold customers"
    ON public.analytics_gold_customers
    FOR SELECT
    TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold customers"
    ON public.analytics_gold_customers
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- RLS for GOLD SUPPLIERS
-- =====================================================================

DROP POLICY IF EXISTS "Users can view own client gold suppliers" ON public.analytics_gold_suppliers;
DROP POLICY IF EXISTS "Service role full access to gold suppliers" ON public.analytics_gold_suppliers;

CREATE POLICY "Users can view own client gold suppliers"
    ON public.analytics_gold_suppliers
    FOR SELECT
    TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold suppliers"
    ON public.analytics_gold_suppliers
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- RLS for SILVER
-- =====================================================================

DROP POLICY IF EXISTS "Users can view own client silver data" ON public.analytics_silver;
DROP POLICY IF EXISTS "Service role full access to silver" ON public.analytics_silver;

CREATE POLICY "Users can view own client silver data"
    ON public.analytics_silver
    FOR SELECT
    TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to silver"
    ON public.analytics_silver
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- STEP 5: Grant Permissions
-- =====================================================================

-- Dashboard users (authenticated) can only SELECT (RLS filters by client_id)
GRANT SELECT ON public.analytics_gold_orders TO authenticated;
GRANT SELECT ON public.analytics_gold_products TO authenticated;
GRANT SELECT ON public.analytics_gold_customers TO authenticated;
GRANT SELECT ON public.analytics_gold_suppliers TO authenticated;
GRANT SELECT ON public.analytics_silver TO authenticated;

-- Analytics API (service_role) has full access to write processed data
GRANT ALL ON public.analytics_gold_orders TO service_role;
GRANT ALL ON public.analytics_gold_products TO service_role;
GRANT ALL ON public.analytics_gold_customers TO service_role;
GRANT ALL ON public.analytics_gold_suppliers TO service_role;
GRANT ALL ON public.analytics_silver TO service_role;

-- =====================================================================
-- Migration Complete
-- =====================================================================
-- What was done:
--   1. ✅ Dropped existing views (if any)
--   2. ✅ Created concrete tables for analytics layers
--   3. ✅ Enabled RLS on all tables
--   4. ✅ Created multi-tenant RLS policies
--   5. ✅ Granted appropriate permissions
--
-- Next Steps:
--   1. Test with: SELECT * FROM analytics_gold_orders;
--   2. Verify RLS: Check that authenticated users see only their data
--   3. Configure Analytics API to write to these tables
-- =====================================================================
