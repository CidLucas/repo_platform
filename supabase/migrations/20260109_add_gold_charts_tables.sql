-- =====================================================================
-- Add Gold Chart Tables for Precomputed Visualizations
-- =====================================================================
-- Purpose: Store precomputed time-series, regional breakdowns, and last orders
-- Created: 2026-01-09
-- Rationale: Avoid loading full Silver dataframe (73k+ rows) on every module page view
-- =====================================================================

-- =====================================================================
-- STEP 1: Create Gold Chart Tables
-- =====================================================================

-- 1. Gold Time Series: Time-based aggregations (e.g., fornecedores_no_tempo)
CREATE TABLE IF NOT EXISTS public.analytics_gold_time_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,

    -- Chart metadata
    chart_type TEXT NOT NULL, -- 'fornecedores_no_tempo', 'clientes_no_tempo', 'pedidos_no_tempo'
    dimension TEXT NOT NULL,  -- What we're counting: 'suppliers', 'customers', 'orders'

    -- Time dimension
    period TEXT NOT NULL,     -- '2025-01', '2025-02', etc. (YYYY-MM format)
    period_date DATE NOT NULL, -- First day of the period for ordering/filtering

    -- Metrics
    total INTEGER DEFAULT 0,  -- Count of unique entities in this period

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_time_series
    ON public.analytics_gold_time_series(client_id, chart_type, dimension, period);

CREATE INDEX IF NOT EXISTS idx_gold_time_series_client ON public.analytics_gold_time_series(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_time_series_period ON public.analytics_gold_time_series(period_date);

COMMENT ON TABLE public.analytics_gold_time_series IS 'Gold layer: Precomputed time-series charts (fornecedores_no_tempo, etc.)';

-- 2. Gold Regional Breakdown: Geographic aggregations
CREATE TABLE IF NOT EXISTS public.analytics_gold_regional (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,

    -- Chart metadata
    chart_type TEXT NOT NULL, -- 'fornecedores_por_regiao', 'clientes_por_regiao', 'pedidos_por_regiao'
    dimension TEXT NOT NULL,  -- 'suppliers', 'customers', 'orders'

    -- Geographic dimension
    region_name TEXT NOT NULL, -- State/city name
    region_type TEXT NOT NULL, -- 'state', 'city'

    -- Metrics
    total INTEGER DEFAULT 0,     -- Count in this region
    contagem INTEGER DEFAULT 0,  -- Alias for total (for schema compatibility)
    percentual DECIMAL(5, 2) DEFAULT 0, -- Percentage of total

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_regional
    ON public.analytics_gold_regional(client_id, chart_type, dimension, region_name, region_type);

CREATE INDEX IF NOT EXISTS idx_gold_regional_client ON public.analytics_gold_regional(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_regional_total ON public.analytics_gold_regional(total DESC);

COMMENT ON TABLE public.analytics_gold_regional IS 'Gold layer: Precomputed regional breakdowns (fornecedores_por_regiao, etc.)';

-- 3. Gold Last Orders: Most recent orders snapshot
CREATE TABLE IF NOT EXISTS public.analytics_gold_last_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,

    -- Order details
    order_id TEXT NOT NULL,
    data_transacao TIMESTAMPTZ NOT NULL,
    id_cliente TEXT,
    ticket_pedido DECIMAL(12, 2) DEFAULT 0,
    qtd_produtos INTEGER DEFAULT 0,

    -- Ranking/ordering
    order_rank INTEGER, -- 1 = most recent

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_last_orders
    ON public.analytics_gold_last_orders(client_id, order_id);

CREATE INDEX IF NOT EXISTS idx_gold_last_orders_client ON public.analytics_gold_last_orders(client_id);
CREATE INDEX IF NOT EXISTS idx_gold_last_orders_date ON public.analytics_gold_last_orders(data_transacao DESC);
CREATE INDEX IF NOT EXISTS idx_gold_last_orders_rank ON public.analytics_gold_last_orders(order_rank) WHERE order_rank <= 20;

COMMENT ON TABLE public.analytics_gold_last_orders IS 'Gold layer: Precomputed last 20 orders for quick retrieval';

-- =====================================================================
-- STEP 2: Enable RLS (Row-Level Security)
-- =====================================================================

ALTER TABLE public.analytics_gold_time_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_regional ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_gold_last_orders ENABLE ROW LEVEL SECURITY;

-- =====================================================================
-- STEP 3: Create RLS Policies (Multi-tenant isolation)
-- =====================================================================

-- Time Series Policies
CREATE POLICY "Users can view their own time series charts"
    ON public.analytics_gold_time_series
    FOR SELECT
    USING (client_id = auth.uid()::text);

CREATE POLICY "Service role can insert time series charts"
    ON public.analytics_gold_time_series
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role can update time series charts"
    ON public.analytics_gold_time_series
    FOR UPDATE
    USING (true);

CREATE POLICY "Service role can delete time series charts"
    ON public.analytics_gold_time_series
    FOR DELETE
    USING (true);

-- Regional Policies
CREATE POLICY "Users can view their own regional charts"
    ON public.analytics_gold_regional
    FOR SELECT
    USING (client_id = auth.uid()::text);

CREATE POLICY "Service role can insert regional charts"
    ON public.analytics_gold_regional
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role can update regional charts"
    ON public.analytics_gold_regional
    FOR UPDATE
    USING (true);

CREATE POLICY "Service role can delete regional charts"
    ON public.analytics_gold_regional
    FOR DELETE
    USING (true);

-- Last Orders Policies
CREATE POLICY "Users can view their own last orders"
    ON public.analytics_gold_last_orders
    FOR SELECT
    USING (client_id = auth.uid()::text);

CREATE POLICY "Service role can insert last orders"
    ON public.analytics_gold_last_orders
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role can update last orders"
    ON public.analytics_gold_last_orders
    FOR UPDATE
    USING (true);

CREATE POLICY "Service role can delete last orders"
    ON public.analytics_gold_last_orders
    FOR DELETE
    USING (true);

-- =====================================================================
-- STEP 4: Grant Permissions
-- =====================================================================

GRANT SELECT ON public.analytics_gold_time_series TO authenticated;
GRANT ALL ON public.analytics_gold_time_series TO service_role;

GRANT SELECT ON public.analytics_gold_regional TO authenticated;
GRANT ALL ON public.analytics_gold_regional TO service_role;

GRANT SELECT ON public.analytics_gold_last_orders TO authenticated;
GRANT ALL ON public.analytics_gold_last_orders TO service_role;

-- =====================================================================
-- STEP 5: Add Helper Function for Cleanup
-- =====================================================================

CREATE OR REPLACE FUNCTION public.cleanup_gold_charts(p_client_id TEXT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Delete existing chart data for this client before recomputing
    DELETE FROM public.analytics_gold_time_series WHERE client_id = p_client_id;
    DELETE FROM public.analytics_gold_regional WHERE client_id = p_client_id;
    DELETE FROM public.analytics_gold_last_orders WHERE client_id = p_client_id;
END;
$$;

COMMENT ON FUNCTION public.cleanup_gold_charts IS 'Helper function to clear all chart data for a client before recompute';
