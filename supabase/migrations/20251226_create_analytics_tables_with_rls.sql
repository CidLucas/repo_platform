-- =====================================================================
-- Analytics Tables with Row Level Security (RLS)
-- =====================================================================
-- Purpose: Create analytics gold layer tables for processed metrics
-- Created: 2025-12-26
-- Architecture:
--   1. Data Ingestion API connects to BigQuery/data sources via FDW
--   2. Analytics API processes data and writes to these gold tables
--   3. Vizu Dashboard reads from gold tables to display metrics
-- =====================================================================

-- =====================================================================
-- GOLD LAYER: Aggregated Analytics Tables (Written by Analytics API)
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
    period_type TEXT, -- 'daily', 'weekly', 'monthly', 'all_time'

    -- Order Status Breakdown (JSONB for flexibility)
    by_status JSONB DEFAULT '{}'::JSONB,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one record per client per period
    CONSTRAINT unique_client_period_orders UNIQUE (client_id, period_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_gold_orders_client_id ON public.analytics_gold_orders(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_orders_period ON public.analytics_gold_orders(period_start, period_end);

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
    period_type TEXT,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_client_product_period UNIQUE (client_id, product_name, period_type, period_start)
);

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
    period_type TEXT,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_client_customer_period UNIQUE (client_id, customer_name, period_type, period_start)
);

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
    period_type TEXT,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_client_supplier_period UNIQUE (client_id, supplier_name, period_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_gold_suppliers_client_id ON public.analytics_gold_suppliers(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_revenue ON public.analytics_gold_suppliers(total_revenue DESC);

COMMENT ON TABLE public.analytics_gold_suppliers IS 'Gold layer: Aggregated supplier metrics written by Analytics API';

-- 5. Analytics Silver (optional - for caching intermediate results in Supabase)
-- This table can store denormalized data from BigQuery for faster access
CREATE TABLE IF NOT EXISTS public.analytics_silver (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    data_transacao TIMESTAMPTZ NOT NULL,

    -- Emitter (Seller) Information
    emitter_nome TEXT,
    emitter_cnpj TEXT,

    -- Receiver (Customer) Information
    receiver_nome TEXT,
    receiver_cpf_cnpj TEXT,

    -- Product Information
    raw_product_description TEXT,
    quantidade DECIMAL(10, 2),
    valor_unitario DECIMAL(10, 2),
    valor_total_emitter DECIMAL(10, 2),

    -- Order Status
    status TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes for performance
    CONSTRAINT unique_client_order_product_silver UNIQUE (client_id, order_id, raw_product_description)
);

CREATE INDEX IF NOT EXISTS idx_analytics_silver_client_id ON public.analytics_silver(client_id);
CREATE INDEX IF NOT EXISTS idx_analytics_silver_data_transacao ON public.analytics_silver(data_transacao);
CREATE INDEX IF NOT EXISTS idx_analytics_silver_order_id ON public.analytics_silver(order_id);

COMMENT ON TABLE public.analytics_silver IS 'Silver layer: Cached denormalized data from BigQuery (optional)';

-- =====================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================================

-- Enable RLS on all analytics tables
ALTER TABLE public.analytics_silver ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_suppliers ENABLE ROW LEVEL SECURITY;

-- =====================================================================
-- RLS for GOLD ORDERS
-- =====================================================================

-- SELECT: Authenticated users can view their own client's data
CREATE POLICY "Users can view own client gold orders"
    ON public.analytics_gold_orders
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT cv.id::text
            FROM public.clientes_vizu cv
            WHERE cv.external_user_id = auth.uid()::text
        )
    );

-- ALL: Service role has full access (Analytics API uses service_role)
CREATE POLICY "Service role full access to gold orders"
    ON public.analytics_gold_orders
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- RLS for GOLD PRODUCTS
-- =====================================================================

CREATE POLICY "Users can view own client gold products"
    ON public.analytics_gold_products
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT cv.id::text
            FROM public.clientes_vizu cv
            WHERE cv.external_user_id = auth.uid()::text
        )
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

CREATE POLICY "Users can view own client gold customers"
    ON public.analytics_gold_customers
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT cv.id::text
            FROM public.clientes_vizu cv
            WHERE cv.external_user_id = auth.uid()::text
        )
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

CREATE POLICY "Users can view own client gold suppliers"
    ON public.analytics_gold_suppliers
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT cv.id::text
            FROM public.clientes_vizu cv
            WHERE cv.external_user_id = auth.uid()::text
        )
    );

CREATE POLICY "Service role full access to gold suppliers"
    ON public.analytics_gold_suppliers
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- RLS for SILVER (optional cache layer)
-- =====================================================================

CREATE POLICY "Users can view own client silver data"
    ON public.analytics_silver
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT cv.id::text
            FROM public.clientes_vizu cv
            WHERE cv.external_user_id = auth.uid()::text
        )
    );

CREATE POLICY "Service role full access to silver"
    ON public.analytics_silver
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================================
-- GRANT PERMISSIONS
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
-- Architecture Summary:
--   Data Flow: BigQuery → Data Ingestion API → Analytics API → Gold Tables → Dashboard
--   Security: RLS ensures users only see their own client_id data
--   Access: service_role (Analytics API) can write, authenticated can read
--
-- Next Steps:
--   1. Apply migration: supabase db push
--   2. Test RLS with authenticated user
--   3. Configure Analytics API to use Supabase service_role key
--   4. Verify Dashboard can read gold tables
-- =====================================================================
