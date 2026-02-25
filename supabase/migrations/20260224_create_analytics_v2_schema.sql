-- =============================================================================
-- Migration: Create analytics_v2 star schema tables
-- Date: 2026-02-24
-- Purpose: Create the analytics_v2 schema with dimension and fact tables
-- =============================================================================

-- 1. CREATE SCHEMA
CREATE SCHEMA IF NOT EXISTS analytics_v2;

-- =============================================================================
-- 2. DIMENSION TABLES
-- =============================================================================

-- dim_customer: Customer dimension with RFM metrics
CREATE TABLE IF NOT EXISTS analytics_v2.dim_customer (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    cpf_cnpj VARCHAR(20),
    name VARCHAR(255),
    telefone VARCHAR(50),
    endereco_rua VARCHAR(255),
    endereco_numero VARCHAR(50),
    endereco_bairro VARCHAR(100),
    endereco_cidade VARCHAR(100),
    endereco_uf VARCHAR(2),
    endereco_cep VARCHAR(10),

    -- Aggregated metrics
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    avg_order_value DECIMAL(15,2) DEFAULT 0,
    total_quantity DECIMAL(15,2) DEFAULT 0,
    orders_last_30_days INTEGER DEFAULT 0,
    frequency_per_month DECIMAL(10,2) DEFAULT 0,
    recency_days INTEGER DEFAULT 0,
    lifetime_start_date DATE,
    lifetime_end_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_client_id ON analytics_v2.dim_customer(client_id);
CREATE INDEX IF NOT EXISTS idx_dim_customer_cpf_cnpj ON analytics_v2.dim_customer(cpf_cnpj);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_customer_unique ON analytics_v2.dim_customer(client_id, cpf_cnpj);

-- dim_supplier: Supplier dimension
CREATE TABLE IF NOT EXISTS analytics_v2.dim_supplier (
    supplier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    cnpj VARCHAR(20),
    name VARCHAR(255),

    -- Aggregated metrics
    total_orders_received INTEGER DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    avg_order_value DECIMAL(15,2) DEFAULT 0,
    total_products_supplied INTEGER DEFAULT 0,
    frequency_per_month DECIMAL(10,2) DEFAULT 0,
    recency_days INTEGER DEFAULT 0,
    first_transaction_date DATE,
    last_transaction_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_supplier_client_id ON analytics_v2.dim_supplier(client_id);
CREATE INDEX IF NOT EXISTS idx_dim_supplier_cnpj ON analytics_v2.dim_supplier(cnpj);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_supplier_unique ON analytics_v2.dim_supplier(client_id, cnpj);

-- dim_product: Product dimension
CREATE TABLE IF NOT EXISTS analytics_v2.dim_product (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    product_name VARCHAR(500),

    -- Aggregated metrics
    total_quantity_sold DECIMAL(15,2) DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    avg_price DECIMAL(15,2) DEFAULT 0,
    number_of_orders INTEGER DEFAULT 0,
    avg_quantity_per_order DECIMAL(10,2) DEFAULT 0,
    frequency_per_month DECIMAL(10,2) DEFAULT 0,
    recency_days INTEGER DEFAULT 0,
    last_sale_date DATE,
    cluster_score DECIMAL(5,2),
    cluster_tier VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_product_client_id ON analytics_v2.dim_product(client_id);
CREATE INDEX IF NOT EXISTS idx_dim_product_name ON analytics_v2.dim_product(product_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_product_unique ON analytics_v2.dim_product(client_id, product_name);

-- =============================================================================
-- 3. FACT TABLE
-- =============================================================================

-- fact_sales: Individual order transactions (grain: order_id, line_item_sequence)
CREATE TABLE IF NOT EXISTS analytics_v2.fact_sales (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    line_item_sequence INTEGER NOT NULL DEFAULT 1,
    order_date DATE,

    -- Foreign keys (denormalized for performance)
    customer_id UUID,
    customer_cpf_cnpj VARCHAR(20),
    customer_name VARCHAR(255),

    supplier_cnpj VARCHAR(20),
    supplier_name VARCHAR(255),

    product_id UUID,
    product_name VARCHAR(500),

    -- Transaction measures
    quantidade DECIMAL(15,2),
    valor_unitario DECIMAL(15,2),
    valor_total DECIMAL(15,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_client_id ON analytics_v2.fact_sales(client_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id ON analytics_v2.fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_date ON analytics_v2.fact_sales(order_date);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_cpf ON analytics_v2.fact_sales(customer_cpf_cnpj);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON analytics_v2.fact_sales(product_name);
CREATE INDEX IF NOT EXISTS idx_fact_sales_supplier_cnpj ON analytics_v2.fact_sales(supplier_cnpj);

-- =============================================================================
-- 4. GRANT PERMISSIONS
-- =============================================================================

GRANT USAGE ON SCHEMA analytics_v2 TO authenticated, service_role, anon;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics_v2 TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA analytics_v2 TO service_role;

-- =============================================================================
-- 5. ROW LEVEL SECURITY (disabled by default - enable after populating)
-- =============================================================================

-- RLS will be enabled by a subsequent migration after data is populated
-- This allows service_role to write without RLS blocking
