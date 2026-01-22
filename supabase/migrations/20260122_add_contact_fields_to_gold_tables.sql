-- =====================================================================
-- Add Contact and Address Fields to Analytics Gold Tables
-- =====================================================================
-- Purpose: Add telefone and endereco fields to gold customer and supplier tables
-- Created: 2026-01-22
-- Changes:
--   1. Add telefone (phone) field to customers and suppliers
--   2. Add endereco_* (address) fields: rua, numero, bairro, cidade, uf, cep
-- =====================================================================

-- =====================================================================
-- ANALYTICS_GOLD_CUSTOMERS: Add Contact Fields
-- =====================================================================

ALTER TABLE public.analytics_gold_customers
ADD COLUMN IF NOT EXISTS telefone TEXT,
ADD COLUMN IF NOT EXISTS endereco_rua TEXT,
ADD COLUMN IF NOT EXISTS endereco_numero TEXT,
ADD COLUMN IF NOT EXISTS endereco_bairro TEXT,
ADD COLUMN IF NOT EXISTS endereco_cidade TEXT,
ADD COLUMN IF NOT EXISTS endereco_uf TEXT,
ADD COLUMN IF NOT EXISTS endereco_cep TEXT;

COMMENT ON COLUMN public.analytics_gold_customers.telefone IS 'Customer phone number';
COMMENT ON COLUMN public.analytics_gold_customers.endereco_rua IS 'Customer street address';
COMMENT ON COLUMN public.analytics_gold_customers.endereco_numero IS 'Customer address number';
COMMENT ON COLUMN public.analytics_gold_customers.endereco_bairro IS 'Customer neighborhood';
COMMENT ON COLUMN public.analytics_gold_customers.endereco_cidade IS 'Customer city';
COMMENT ON COLUMN public.analytics_gold_customers.endereco_uf IS 'Customer state/UF';
COMMENT ON COLUMN public.analytics_gold_customers.endereco_cep IS 'Customer postal code/CEP';

-- Create index for location-based queries
CREATE INDEX IF NOT EXISTS idx_gold_customers_cidade ON public.analytics_gold_customers(endereco_cidade);
CREATE INDEX IF NOT EXISTS idx_gold_customers_uf ON public.analytics_gold_customers(endereco_uf);

-- =====================================================================
-- ANALYTICS_GOLD_SUPPLIERS: Add Contact Fields
-- =====================================================================

ALTER TABLE public.analytics_gold_suppliers
ADD COLUMN IF NOT EXISTS telefone TEXT,
ADD COLUMN IF NOT EXISTS endereco_rua TEXT,
ADD COLUMN IF NOT EXISTS endereco_numero TEXT,
ADD COLUMN IF NOT EXISTS endereco_bairro TEXT,
ADD COLUMN IF NOT EXISTS endereco_cidade TEXT,
ADD COLUMN IF NOT EXISTS endereco_uf TEXT,
ADD COLUMN IF NOT EXISTS endereco_cep TEXT;

COMMENT ON COLUMN public.analytics_gold_suppliers.telefone IS 'Supplier phone number';
COMMENT ON COLUMN public.analytics_gold_suppliers.endereco_rua IS 'Supplier street address';
COMMENT ON COLUMN public.analytics_gold_suppliers.endereco_numero IS 'Supplier address number';
COMMENT ON COLUMN public.analytics_gold_suppliers.endereco_bairro IS 'Supplier neighborhood';
COMMENT ON COLUMN public.analytics_gold_suppliers.endereco_cidade IS 'Supplier city';
COMMENT ON COLUMN public.analytics_gold_suppliers.endereco_uf IS 'Supplier state/UF';
COMMENT ON COLUMN public.analytics_gold_suppliers.endereco_cep IS 'Supplier postal code/CEP';

-- Create index for location-based queries
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_cidade ON public.analytics_gold_suppliers(endereco_cidade);
CREATE INDEX IF NOT EXISTS idx_gold_suppliers_uf ON public.analytics_gold_suppliers(endereco_uf);
