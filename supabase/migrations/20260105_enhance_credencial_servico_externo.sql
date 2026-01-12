-- Migration: Enhance credencial_servico_externo table
-- Purpose: Add missing metadata columns for better connector tracking
-- Date: 2026-01-05

-- Add new columns for credential metadata (IF NOT EXISTS to be safe)
ALTER TABLE credencial_servico_externo
    ADD COLUMN IF NOT EXISTS tipo_servico TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'error', 'pending')),
    ADD COLUMN IF NOT EXISTS credenciais_cifradas TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add index for status
CREATE INDEX IF NOT EXISTS idx_credencial_status ON credencial_servico_externo(status);

-- Add trigger for updated_at (if function exists from previous migration)
DROP TRIGGER IF EXISTS trigger_update_credencial_servico_externo_updated_at ON credencial_servico_externo;

CREATE TRIGGER trigger_update_credencial_servico_externo_updated_at
    BEFORE UPDATE ON credencial_servico_externo
    FOR EACH ROW
    EXECUTE FUNCTION update_connector_sync_history_updated_at();

-- Comments
COMMENT ON COLUMN credencial_servico_externo.tipo_servico IS 'Type of service: BIGQUERY, SHOPIFY, VTEX, POSTGRES, MYSQL, etc.';
COMMENT ON COLUMN credencial_servico_externo.status IS 'Connection status: active, inactive, error, or pending';
COMMENT ON COLUMN credencial_servico_externo.credenciais_cifradas IS 'Secret Manager ID or encrypted credentials reference';
