-- ============================================================================
-- Verify and Fix credencial_servico_externo Table
-- Run this in Supabase SQL Editor
-- ============================================================================

-- Step 1: Check current table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'credencial_servico_externo'
ORDER BY ordinal_position;

-- Step 2: Add missing columns if they don't exist
ALTER TABLE public.credencial_servico_externo
    ADD COLUMN IF NOT EXISTS tipo_servico TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'
        CHECK (status IN ('active', 'inactive', 'error', 'pending')),
    ADD COLUMN IF NOT EXISTS credenciais_cifradas TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Step 3: Create index for status if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_credencial_status
    ON public.credencial_servico_externo(status);

-- Step 4: Create or replace updated_at trigger function
CREATE OR REPLACE FUNCTION public.update_credencial_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger for updated_at
DROP TRIGGER IF EXISTS trigger_credencial_updated_at ON public.credencial_servico_externo;

CREATE TRIGGER trigger_credencial_updated_at
    BEFORE UPDATE ON public.credencial_servico_externo
    FOR EACH ROW
    EXECUTE FUNCTION public.update_credencial_updated_at();

-- Step 6: Verify the changes
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'credencial_servico_externo'
ORDER BY ordinal_position;

-- Step 7: Check if table has data
SELECT
    COUNT(*) as total_records,
    COUNT(CASE WHEN tipo_servico IS NOT NULL THEN 1 END) as with_tipo_servico,
    COUNT(CASE WHEN credenciais_cifradas IS NOT NULL THEN 1 END) as with_credentials
FROM public.credencial_servico_externo;
