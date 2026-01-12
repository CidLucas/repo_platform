-- =====================================================================
-- Data Source Registry & Raw Data Tables
-- =====================================================================
-- Purpose: Unified registry for all data sources (BigQuery, CSV, VTEX, etc.)
-- Created: 2026-01-06
-- =====================================================================

-- 1. Data Source Registry: Tracks where each client's data is stored
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.client_data_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT NOT NULL,

  -- Source identification
  source_type TEXT NOT NULL,  -- 'bigquery', 'csv', 'vtex', 'shopify', etc.
  resource_type TEXT NOT NULL,  -- 'invoices', 'products', 'orders', etc.

  -- Where the data is stored
  storage_type TEXT NOT NULL,  -- 'foreign_table', 'jsonb_table', 'bucket'
  storage_location TEXT NOT NULL,  -- Table name or bucket path

  -- Schema information
  column_mapping JSONB,  -- Maps source columns to canonical schema
  -- Example: {"order_id": "id_pedido", "customer_name": "nome_cliente"}

  -- Metadata
  last_synced_at TIMESTAMPTZ,
  sync_status TEXT DEFAULT 'pending',  -- 'pending', 'active', 'error'
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Unique constraint: one source per (client, source_type, resource_type)
  CONSTRAINT unique_client_source_resource UNIQUE (client_id, source_type, resource_type)
);

CREATE INDEX IF NOT EXISTS idx_client_data_sources_client_id
  ON public.client_data_sources(client_id);

CREATE INDEX IF NOT EXISTS idx_client_data_sources_source_type
  ON public.client_data_sources(source_type);

COMMENT ON TABLE public.client_data_sources IS
  'Registry of all data sources for each client (BigQuery foreign tables, CSV uploads, API connectors)';

-- =====================================================================
-- 2. Raw Data JSONB Table: For CSV/VTEX/API data (flexible schema)
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.raw_data_jsonb (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT NOT NULL,

  -- Source identification
  source_type TEXT NOT NULL,  -- 'csv', 'vtex', 'shopify'
  resource_type TEXT NOT NULL,  -- 'invoices', 'products', etc.

  -- Flexible data storage
  raw_data JSONB NOT NULL,  -- Entire row from CSV/API as JSON

  -- Metadata
  source_file TEXT,  -- Original filename or API endpoint
  row_number INTEGER,  -- Row number in original source

  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- Index for fast client queries
  CONSTRAINT idx_raw_data_client_source UNIQUE (client_id, source_type, resource_type, row_number)
);

CREATE INDEX IF NOT EXISTS idx_raw_data_jsonb_client_id
  ON public.raw_data_jsonb(client_id);

CREATE INDEX IF NOT EXISTS idx_raw_data_jsonb_source
  ON public.raw_data_jsonb(source_type, resource_type);

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_raw_data_jsonb_data
  ON public.raw_data_jsonb USING gin(raw_data);

COMMENT ON TABLE public.raw_data_jsonb IS
  'Temporary storage for CSV/API data in flexible JSONB format';

-- =====================================================================
-- 3. Enable RLS
-- =====================================================================
ALTER TABLE public.client_data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.raw_data_jsonb ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own data sources
CREATE POLICY client_data_sources_policy ON public.client_data_sources
  FOR ALL
  USING (client_id = current_setting('app.current_client_id', true));

CREATE POLICY raw_data_jsonb_policy ON public.raw_data_jsonb
  FOR ALL
  USING (client_id = current_setting('app.current_client_id', true));

-- =====================================================================
-- 4. Helper Functions
-- =====================================================================

-- Function: Register a new data source
CREATE OR REPLACE FUNCTION public.register_data_source(
  p_client_id TEXT,
  p_source_type TEXT,
  p_resource_type TEXT,
  p_storage_type TEXT,
  p_storage_location TEXT,
  p_column_mapping JSONB DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
  v_source_id UUID;
BEGIN
  -- Upsert data source registration
  INSERT INTO public.client_data_sources (
    client_id,
    source_type,
    resource_type,
    storage_type,
    storage_location,
    column_mapping,
    sync_status
  ) VALUES (
    p_client_id,
    p_source_type,
    p_resource_type,
    p_storage_type,
    p_storage_location,
    p_column_mapping,
    'active'
  )
  ON CONFLICT (client_id, source_type, resource_type)
  DO UPDATE SET
    storage_type = EXCLUDED.storage_type,
    storage_location = EXCLUDED.storage_location,
    column_mapping = EXCLUDED.column_mapping,
    sync_status = 'active',
    updated_at = NOW()
  RETURNING id INTO v_source_id;

  RETURN jsonb_build_object(
    'success', true,
    'source_id', v_source_id,
    'storage_location', p_storage_location
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.register_data_source IS
  'Registers or updates a data source for a client';

-- Function: Get data source for client
CREATE OR REPLACE FUNCTION public.get_data_source(
  p_client_id TEXT,
  p_source_type TEXT,
  p_resource_type TEXT
) RETURNS JSONB AS $$
DECLARE
  v_result JSONB;
BEGIN
  SELECT jsonb_build_object(
    'source_id', id,
    'storage_type', storage_type,
    'storage_location', storage_location,
    'column_mapping', column_mapping,
    'sync_status', sync_status,
    'last_synced_at', last_synced_at
  )
  INTO v_result
  FROM public.client_data_sources
  WHERE client_id = p_client_id
    AND source_type = p_source_type
    AND resource_type = p_resource_type;

  IF v_result IS NULL THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', 'Data source not found'
    );
  END IF;

  RETURN jsonb_build_object(
    'success', true,
    'data', v_result
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.client_data_sources TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.raw_data_jsonb TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.register_data_source TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_data_source TO authenticated, service_role;

-- =====================================================================
-- Migration Complete
-- =====================================================================
