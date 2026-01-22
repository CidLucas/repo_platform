-- =====================================================================
-- Create analytics_gold_customer_products Table
-- =====================================================================
-- Purpose: Pre-aggregated product metrics per customer for fast lookups
-- This enables the gold endpoint to show "top products by customer" without
-- querying the silver layer (BigQuery FDW).
--
-- Use Case: ClienteDetailsModal displays mix_de_produtos_por_receita
-- which shows the top products purchased by a specific customer.
--
-- Created: 2026-01-22
-- =====================================================================

CREATE TABLE IF NOT EXISTS public.analytics_gold_customer_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,

    -- Customer identification
    customer_cpf_cnpj TEXT NOT NULL,
    customer_name TEXT,

    -- Product identification
    product_name TEXT NOT NULL,

    -- Aggregated metrics for this customer-product combination
    receita_total NUMERIC(12, 2) DEFAULT 0,
    quantidade_total NUMERIC(12, 2) DEFAULT 0,
    num_pedidos INTEGER DEFAULT 0,
    valor_unitario_medio NUMERIC(10, 2) DEFAULT 0,

    -- Time tracking
    primeira_compra TIMESTAMPTZ,
    ultima_compra TIMESTAMPTZ,

    -- Metadata
    period_type TEXT DEFAULT 'all_time',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================================
-- INDEXES
-- =====================================================================

-- Primary lookup: Get products for a specific customer (sorted by revenue)
CREATE INDEX IF NOT EXISTS idx_gold_customer_products_lookup
    ON public.analytics_gold_customer_products(client_id, customer_cpf_cnpj, receita_total DESC);

-- Prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_gold_customer_product
    ON public.analytics_gold_customer_products(client_id, customer_cpf_cnpj, product_name, period_type);

-- =====================================================================
-- COMMENTS
-- =====================================================================

COMMENT ON TABLE public.analytics_gold_customer_products IS
    'Pre-aggregated product metrics per customer. Populated during ETL recompute. Used by ClienteDetailsModal.';

COMMENT ON COLUMN public.analytics_gold_customer_products.customer_cpf_cnpj IS
    'Customer CPF/CNPJ - links to analytics_gold_customers.customer_cpf_cnpj';

COMMENT ON COLUMN public.analytics_gold_customer_products.receita_total IS
    'Total revenue from this product for this customer';

COMMENT ON COLUMN public.analytics_gold_customer_products.quantidade_total IS
    'Total quantity of this product purchased by this customer';

-- =====================================================================
-- RLS POLICY
-- =====================================================================

ALTER TABLE public.analytics_gold_customer_products ENABLE ROW LEVEL SECURITY;

-- Policy: Service role has full access (for ETL writes)
CREATE POLICY "analytics_gold_customer_products_service_access"
    ON public.analytics_gold_customer_products
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy: Authenticated users can read their own client's data
CREATE POLICY "analytics_gold_customer_products_client_read"
    ON public.analytics_gold_customer_products
    FOR SELECT
    TO authenticated
    USING (client_id = current_setting('app.client_id', true));
