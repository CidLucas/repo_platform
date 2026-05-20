-- Add Google Drive metadata columns to client_data_sources.
-- Required by upload-drive-source which inserts drive_file_id, drive_modified_time,
-- and integration_token_id (UUID FK to integration_tokens.id).
-- credential_id (BIGINT) is kept null for Drive sources; the UUID link lives here.

ALTER TABLE public.client_data_sources
  ADD COLUMN IF NOT EXISTS drive_file_id TEXT,
  ADD COLUMN IF NOT EXISTS drive_modified_time TEXT,
  ADD COLUMN IF NOT EXISTS integration_token_id UUID REFERENCES public.integration_tokens(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_cds_integration_token
  ON public.client_data_sources (integration_token_id)
  WHERE integration_token_id IS NOT NULL;
