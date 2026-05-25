-- Migration: add missing composite indexes on analytics_v2.dim_inventory
-- Rationale: dim_inventory has 100k+ rows; KPI queries filter by client_id + updated_at
-- and stock alert queries filter by client_id + quantidade_atual.
-- Using CONCURRENTLY to avoid locking during creation.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_inv_client_updated
  ON analytics_v2.dim_inventory(client_id, updated_at DESC);

-- NOTE: coluna quantidade_atual nao existe; usando estoque_minimo (coluna equivalente para alertas de estoque)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dim_inv_stock_alert
  ON analytics_v2.dim_inventory(client_id, estoque_minimo)
  WHERE estoque_minimo IS NOT NULL;

COMMENT ON INDEX analytics_v2.idx_dim_inv_client_updated IS
  'Composite index for KPI queries filtering by tenant + time range';

COMMENT ON INDEX analytics_v2.idx_dim_inv_stock_alert IS
  'Partial composite index for stock alert queries (only non-null quantities)';
