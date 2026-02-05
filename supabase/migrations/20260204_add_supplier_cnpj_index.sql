-- Migration: Add index on supplier_cnpj for query performance
-- This index improves JOIN performance between dim_supplier and fact_sales

-- Add index for supplier_cnpj lookups (used in JOINs with dim_supplier)
CREATE INDEX IF NOT EXISTS idx_fact_sales_supplier_cnpj
ON analytics_v2.fact_sales(supplier_cnpj);
