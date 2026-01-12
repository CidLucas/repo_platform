-- =====================================================================
-- COPY THIS ENTIRE FILE AND PASTE INTO SUPABASE SQL EDITOR
-- =====================================================================
-- Instructions:
--   1. Open Supabase Dashboard: https://supabase.com/dashboard
--   2. Go to SQL Editor
--   3. Click "New Query"
--   4. Copy this ENTIRE file
--   5. Paste into the editor
--   6. Click "Run" or press Cmd+Enter
-- =====================================================================

-- Clean up existing views and tables
-- Drop views first (if they exist)
DROP VIEW IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_customers CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_products CASCADE;
DROP VIEW IF EXISTS public.analytics_gold_orders CASCADE;
DROP VIEW IF EXISTS public.analytics_silver CASCADE;

-- Drop tables (if they exist without RLS)
-- This ensures we start fresh with RLS-enabled tables
DROP TABLE IF EXISTS public.analytics_gold_suppliers CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_customers CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_products CASCADE;
DROP TABLE IF EXISTS public.analytics_gold_orders CASCADE;
DROP TABLE IF EXISTS public.analytics_silver CASCADE;

-- Create tables
CREATE TABLE IF NOT EXISTS public.analytics_gold_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',
    by_status JSONB DEFAULT '{}'::JSONB,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.analytics_gold_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    total_quantity_sold DECIMAL(12, 2) DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,
    avg_price DECIMAL(10, 2) DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    revenue_rank INTEGER,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.analytics_gold_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_cpf_cnpj TEXT,
    total_orders INTEGER DEFAULT 0,
    lifetime_value DECIMAL(12, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,
    first_order_date TIMESTAMPTZ,
    last_order_date TIMESTAMPTZ,
    customer_type TEXT,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.analytics_gold_suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    supplier_cnpj TEXT,
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,
    unique_products INTEGER DEFAULT 0,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    period_type TEXT DEFAULT 'all_time',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_gold_orders_client_id ON public.analytics_gold_orders(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_products_client_id ON public.analytics_gold_products(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_customers_client_id ON public.analytics_gold_customers(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_client_id ON public.analytics_gold_suppliers(client_id);
CREATE INDEX IF NOT EXISTS idx_analytics_silver_client_id ON public.analytics_silver(client_id);

-- Enable RLS
ALTER TABLE public.analytics_gold_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_silver ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own client gold orders" ON public.analytics_gold_orders;
DROP POLICY IF EXISTS "Service role full access to gold orders" ON public.analytics_gold_orders;
DROP POLICY IF EXISTS "Users can view own client gold products" ON public.analytics_gold_products;
DROP POLICY IF EXISTS "Service role full access to gold products" ON public.analytics_gold_products;
DROP POLICY IF EXISTS "Users can view own client gold customers" ON public.analytics_gold_customers;
DROP POLICY IF EXISTS "Service role full access to gold customers" ON public.analytics_gold_customers;
DROP POLICY IF EXISTS "Users can view own client gold suppliers" ON public.analytics_gold_suppliers;
DROP POLICY IF EXISTS "Service role full access to gold suppliers" ON public.analytics_gold_suppliers;
DROP POLICY IF EXISTS "Users can view own client silver data" ON public.analytics_silver;
DROP POLICY IF EXISTS "Service role full access to silver" ON public.analytics_silver;

-- Create RLS policies for gold_orders
CREATE POLICY "Users can view own client gold orders"
    ON public.analytics_gold_orders FOR SELECT TO authenticated
    USING (
        -- Allow if client_id matches the client_id from JWT claims
        client_id = (auth.jwt()->>'client_id')::text
        OR
        -- Allow if client_id exists in cliente_vizu table (fallback)
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold orders"
    ON public.analytics_gold_orders FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Create RLS policies for gold_products
CREATE POLICY "Users can view own client gold products"
    ON public.analytics_gold_products FOR SELECT TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold products"
    ON public.analytics_gold_products FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Create RLS policies for gold_customers
CREATE POLICY "Users can view own client gold customers"
    ON public.analytics_gold_customers FOR SELECT TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold customers"
    ON public.analytics_gold_customers FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Create RLS policies for gold_suppliers
CREATE POLICY "Users can view own client gold suppliers"
    ON public.analytics_gold_suppliers FOR SELECT TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to gold suppliers"
    ON public.analytics_gold_suppliers FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Create RLS policies for silver
CREATE POLICY "Users can view own client silver data"
    ON public.analytics_silver FOR SELECT TO authenticated
    USING (
        client_id = (auth.jwt()->>'client_id')::text
        OR
        client_id IN (SELECT id::text FROM public.cliente_vizu)
    );

CREATE POLICY "Service role full access to silver"
    ON public.analytics_silver FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Grant permissions
GRANT SELECT ON public.analytics_gold_orders TO authenticated;
GRANT SELECT ON public.analytics_gold_products TO authenticated;
GRANT SELECT ON public.analytics_gold_customers TO authenticated;
GRANT SELECT ON public.analytics_gold_suppliers TO authenticated;
GRANT SELECT ON public.analytics_silver TO authenticated;

GRANT ALL ON public.analytics_gold_orders TO service_role;
GRANT ALL ON public.analytics_gold_products TO service_role;
GRANT ALL ON public.analytics_gold_customers TO service_role;
GRANT ALL ON public.analytics_gold_suppliers TO service_role;
GRANT ALL ON public.analytics_silver TO service_role;

-- =====================================================================
-- DONE! Now verify:
-- =====================================================================
-- Run these queries to check everything is working:

-- 1. Check tables exist
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'analytics_%';

-- 2. Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename LIKE 'analytics_%';

-- 3. Check policies exist
SELECT tablename, policyname, roles
FROM pg_policies
WHERE tablename LIKE 'analytics_%';
