-- Add missing columns to client_data_sources table for auto-discovery
-- The discovery migration expects these columns but they weren't in the original schema

ALTER TABLE public.client_data_sources
ADD COLUMN IF NOT EXISTS source_columns JSONB COMMENT 'Auto-discovered columns from source';

ALTER TABLE public.client_data_sources
ADD COLUMN IF NOT EXISTS source_sample_data JSONB COMMENT 'Sample data rows from source for preview';

ALTER TABLE public.client_data_sources
ADD COLUMN IF NOT EXISTS credential_id BIGINT REFERENCES credencial_servico_externo(id)
COMMENT 'Reference to the credential used to access this data source';

-- Create index for faster lookups by credential_id
CREATE INDEX IF NOT EXISTS idx_client_data_sources_credential_id
  ON public.client_data_sources(credential_id);

-- Rename atualizado_em to updated_at for consistency (if it was added)
-- The discovery functions expect updated_at but we use atualizado_em elsewhere
-- Keep both for compatibility
ALTER TABLE public.client_data_sources
ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ DEFAULT NOW()
COMMENT 'Portuguese-Portuguese timestamp for compatibility';

-- Create a trigger to auto-update atualizado_em
CREATE OR REPLACE FUNCTION update_client_data_sources_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = NOW();
  return NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_client_data_sources_atualizado_em ON public.client_data_sources;

CREATE TRIGGER trg_update_client_data_sources_atualizado_em
BEFORE UPDATE ON public.client_data_sources
FOR EACH ROW
EXECUTE FUNCTION update_client_data_sources_atualizado_em();
