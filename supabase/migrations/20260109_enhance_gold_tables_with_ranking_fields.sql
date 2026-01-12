-- =====================================================================
-- Analytics Gold Tables Enhancement: Add RankingItem Fields
-- =====================================================================
-- Purpose: Add all RankingItem fields to gold tables for complete metrics
-- Created: 2026-01-09
-- Changes:
--   1. Add quantity and frequency metrics to all gold tables
--   2. Add RFM (Recency, Frequency, Monetary) scoring fields
--   3. Add cluster tier segmentation fields
--   4. Add date range tracking (primeira_venda, ultima_venda)
-- =====================================================================

-- =====================================================================
-- ANALYTICS_GOLD_CUSTOMERS: Add RankingItem Fields
-- =====================================================================

ALTER TABLE public.analytics_gold_customers
ADD COLUMN IF NOT EXISTS quantidade_total DECIMAL(12, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS num_pedidos_unicos INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ticket_medio DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS qtd_media_por_pedido DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS frequencia_pedidos_mes DECIMAL(10, 4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS recencia_dias INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS valor_unitario_medio DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS cluster_score DECIMAL(5, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS cluster_tier TEXT,
ADD COLUMN IF NOT EXISTS primeira_venda TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS ultima_venda TIMESTAMPTZ;

COMMENT ON COLUMN public.analytics_gold_customers.quantidade_total IS 'Total quantity purchased by customer';
COMMENT ON COLUMN public.analytics_gold_customers.num_pedidos_unicos IS 'Unique number of orders';
COMMENT ON COLUMN public.analytics_gold_customers.ticket_medio IS 'Average order value (receita/num_pedidos)';
COMMENT ON COLUMN public.analytics_gold_customers.qtd_media_por_pedido IS 'Average quantity per order';
COMMENT ON COLUMN public.analytics_gold_customers.frequencia_pedidos_mes IS 'Orders per month frequency';
COMMENT ON COLUMN public.analytics_gold_customers.recencia_dias IS 'Days since last purchase';
COMMENT ON COLUMN public.analytics_gold_customers.valor_unitario_medio IS 'Average unit value';
COMMENT ON COLUMN public.analytics_gold_customers.cluster_score IS 'RFM cluster score (0-100)';
COMMENT ON COLUMN public.analytics_gold_customers.cluster_tier IS 'Customer segment (A, B, C, D)';
COMMENT ON COLUMN public.analytics_gold_customers.primeira_venda IS 'Date of first purchase';
COMMENT ON COLUMN public.analytics_gold_customers.ultima_venda IS 'Date of last purchase';

-- Create index for cluster_tier queries
CREATE INDEX IF NOT EXISTS idx_gold_customers_cluster_tier ON public.analytics_gold_customers(cluster_tier);
CREATE INDEX IF NOT EXISTS idx_gold_customers_cluster_score ON public.analytics_gold_customers(cluster_score DESC);

-- =====================================================================
-- ANALYTICS_GOLD_SUPPLIERS: Add RankingItem Fields
-- =====================================================================

ALTER TABLE public.analytics_gold_suppliers
ADD COLUMN IF NOT EXISTS quantidade_total DECIMAL(12, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS num_pedidos_unicos INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ticket_medio DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS qtd_media_por_pedido DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS frequencia_pedidos_mes DECIMAL(10, 4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS recencia_dias INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS valor_unitario_medio DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS cluster_score DECIMAL(5, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS cluster_tier TEXT,
ADD COLUMN IF NOT EXISTS primeira_venda TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS ultima_venda TIMESTAMPTZ;

COMMENT ON COLUMN public.analytics_gold_suppliers.quantidade_total IS 'Total quantity supplied';
COMMENT ON COLUMN public.analytics_gold_suppliers.num_pedidos_unicos IS 'Unique number of supply orders';
COMMENT ON COLUMN public.analytics_gold_suppliers.ticket_medio IS 'Average order value';
COMMENT ON COLUMN public.analytics_gold_suppliers.qtd_media_por_pedido IS 'Average quantity per order';
COMMENT ON COLUMN public.analytics_gold_suppliers.frequencia_pedidos_mes IS 'Orders per month frequency';
COMMENT ON COLUMN public.analytics_gold_suppliers.recencia_dias IS 'Days since last supply order';
COMMENT ON COLUMN public.analytics_gold_suppliers.valor_unitario_medio IS 'Average unit value';
COMMENT ON COLUMN public.analytics_gold_suppliers.cluster_score IS 'RFM cluster score (0-100)';
COMMENT ON COLUMN public.analytics_gold_suppliers.cluster_tier IS 'Supplier segment (A, B, C, D)';
COMMENT ON COLUMN public.analytics_gold_suppliers.primeira_venda IS 'Date of first supply order';
COMMENT ON COLUMN public.analytics_gold_suppliers.ultima_venda IS 'Date of last supply order';

-- Create index for cluster_tier queries
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_cluster_tier ON public.analytics_gold_suppliers(cluster_tier);
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_cluster_score ON public.analytics_gold_suppliers(cluster_score DESC);

-- =====================================================================
-- ANALYTICS_GOLD_PRODUCTS: Add RankingItem Fields
-- =====================================================================

ALTER TABLE public.analytics_gold_products
ADD COLUMN IF NOT EXISTS quantidade_total DECIMAL(12, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS num_pedidos_unicos INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ticket_medio DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS qtd_media_por_pedido DECIMAL(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS frequencia_pedidos_mes DECIMAL(10, 4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS recencia_dias INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS cluster_score DECIMAL(5, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS cluster_tier TEXT,
ADD COLUMN IF NOT EXISTS primeira_venda TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS ultima_venda TIMESTAMPTZ;

COMMENT ON COLUMN public.analytics_gold_products.quantidade_total IS 'Already exists as total_quantity_sold - total items sold';
COMMENT ON COLUMN public.analytics_gold_products.num_pedidos_unicos IS 'Already exists as order_count - unique orders';
COMMENT ON COLUMN public.analytics_gold_products.ticket_medio IS 'Average revenue per order';
COMMENT ON COLUMN public.analytics_gold_products.qtd_media_por_pedido IS 'Average quantity per order';
COMMENT ON COLUMN public.analytics_gold_products.frequencia_pedidos_mes IS 'Orders per month frequency';
COMMENT ON COLUMN public.analytics_gold_products.recencia_dias IS 'Days since last sale';
COMMENT ON COLUMN public.analytics_gold_products.cluster_score IS 'Product performance score (0-100)';
COMMENT ON COLUMN public.analytics_gold_products.cluster_tier IS 'Product tier (A, B, C, D)';
COMMENT ON COLUMN public.analytics_gold_products.primeira_venda IS 'Date of first sale';
COMMENT ON COLUMN public.analytics_gold_products.ultima_venda IS 'Date of last sale';

-- Create index for cluster_tier queries
CREATE INDEX IF NOT EXISTS idx_gold_products_cluster_tier ON public.analytics_gold_products(cluster_tier);
CREATE INDEX IF NOT EXISTS idx_gold_products_cluster_score ON public.analytics_gold_products(cluster_score DESC);

-- =====================================================================
-- ANALYTICS_GOLD_ORDERS: Add RankingItem Fields (if applicable)
-- =====================================================================

-- Note: Orders table is for aggregate metrics, not individual rankings
-- Add basic tracking fields for completeness
ALTER TABLE public.analytics_gold_orders
ADD COLUMN IF NOT EXISTS quantidade_total DECIMAL(12, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS frequencia_pedidos_mes DECIMAL(10, 4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS recencia_dias INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS primeira_transacao TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS ultima_transacao TIMESTAMPTZ;

COMMENT ON COLUMN public.analytics_gold_orders.quantidade_total IS 'Total items across all orders';
COMMENT ON COLUMN public.analytics_gold_orders.frequencia_pedidos_mes IS 'Average orders per month';
COMMENT ON COLUMN public.analytics_gold_orders.recencia_dias IS 'Days since last order in period';
COMMENT ON COLUMN public.analytics_gold_orders.primeira_transacao IS 'Date of first order in period';
COMMENT ON COLUMN public.analytics_gold_orders.ultima_transacao IS 'Date of last order in period';

-- =====================================================================
-- Verify Migration
-- =====================================================================

-- Check that all columns were added successfully
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('analytics_gold_customers', 'analytics_gold_suppliers', 'analytics_gold_products', 'analytics_gold_orders')
  AND column_name IN (
    'quantidade_total', 'num_pedidos_unicos', 'ticket_medio', 'qtd_media_por_pedido',
    'frequencia_pedidos_mes', 'recencia_dias', 'valor_unitario_medio', 'cluster_score', 'cluster_tier',
    'primeira_venda', 'ultima_venda'
  )
ORDER BY table_name, ordinal_position;
