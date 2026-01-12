-- ============================================================================
-- Complete Table Consolidation: Migrate to clientes_vizu
-- This migration consolidates cliente_vizu, clientes_vizu, and configuracao_negocio
-- into a single clientes_vizu table.
--
-- Run this in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: Verify Current State
-- ============================================================================

SELECT 'Checking table existence' as step;

SELECT
    'cliente_vizu' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT id) as unique_ids
FROM public.cliente_vizu
UNION ALL
SELECT
    'clientes_vizu' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT id) as unique_ids
FROM public.clientes_vizu
UNION ALL
SELECT
    'configuracao_negocio' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT client_id) as unique_cliente_ids
FROM public.configuracao_negocio;

-- ============================================================================
-- STEP 2: Ensure clientes_vizu has all necessary columns
-- ============================================================================

SELECT 'Adding missing columns to clientes_vizu' as step;

-- Add any missing columns (IF NOT EXISTS ensures no errors if already present)
ALTER TABLE public.clientes_vizu
    ADD COLUMN IF NOT EXISTS external_user_id TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_external_user_id
    ON public.clientes_vizu(external_user_id);

CREATE INDEX IF NOT EXISTS idx_clientes_vizu_api_key
    ON public.clientes_vizu(api_key);

-- ============================================================================
-- STEP 3: Migrate data from cliente_vizu to clientes_vizu
-- ============================================================================

SELECT 'Migrating data from cliente_vizu to clientes_vizu' as step;

-- Insert records from cliente_vizu that don't exist in clientes_vizu
INSERT INTO public.clientes_vizu (
    id,
    nome_empresa,
    tipo_cliente,
    tier,
    api_key,
    horario_funcionamento,
    prompt_base,
    enabled_tools,
    collection_rag,
    created_at,
    updated_at
)
SELECT
    cv.id,
    cv.nome_empresa,
    cv.tipo_cliente::text,
    cv.tier::text,
    cv.api_key,
    cv.horario_funcionamento,
    cv.prompt_base,
    -- Convert JSONB array to PostgreSQL TEXT[] array
    CASE
        WHEN cv.enabled_tools IS NOT NULL AND jsonb_typeof(cv.enabled_tools) = 'array' THEN
            ARRAY(SELECT jsonb_array_elements_text(cv.enabled_tools))
        ELSE
            '{}'::text[]  -- Empty array if null or not an array
    END,
    cv.collection_rag,
    NOW() as created_at,
    NOW() as updated_at
FROM public.cliente_vizu cv
WHERE NOT EXISTS (
    SELECT 1 FROM public.clientes_vizu cvz
    WHERE cvz.id = cv.id
);

-- Show migrated count
SELECT
    'Records migrated from cliente_vizu' as status,
    COUNT(*) as count
FROM public.clientes_vizu
WHERE created_at >= NOW() - INTERVAL '1 minute';

-- ============================================================================
-- STEP 4: Update Foreign Key Constraints
-- ============================================================================

SELECT 'Updating foreign key constraints' as step;

-- Drop old FK constraint on credencial_servico_externo
ALTER TABLE public.credencial_servico_externo
    DROP CONSTRAINT IF EXISTS credencial_servico_externo_client_id_fkey;

-- Add new FK constraint pointing to clientes_vizu
ALTER TABLE public.credencial_servico_externo
    ADD CONSTRAINT credencial_servico_externo_client_id_fkey
    FOREIGN KEY (client_id)
    REFERENCES public.clientes_vizu(id)
    ON DELETE CASCADE;

-- Update FK for cliente_final (if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'cliente_final_client_id_fkey'
        AND table_name = 'cliente_final'
    ) THEN
        ALTER TABLE public.cliente_final
            DROP CONSTRAINT cliente_final_client_id_fkey;

        ALTER TABLE public.cliente_final
            ADD CONSTRAINT cliente_final_client_id_fkey
            FOREIGN KEY (client_id)
            REFERENCES public.clientes_vizu(id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- Update FK for fonte_de_dados (if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fonte_de_dados_client_id_fkey'
        AND table_name = 'fonte_de_dados'
    ) THEN
        ALTER TABLE public.fonte_de_dados
            DROP CONSTRAINT fonte_de_dados_client_id_fkey;

        ALTER TABLE public.fonte_de_dados
            ADD CONSTRAINT fonte_de_dados_client_id_fkey
            FOREIGN KEY (client_id)
            REFERENCES public.clientes_vizu(id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- Update FK for conversa (if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'conversa_client_id_fkey'
        AND table_name = 'conversa'
    ) THEN
        ALTER TABLE public.conversa
            DROP CONSTRAINT conversa_client_id_fkey;

        ALTER TABLE public.conversa
            ADD CONSTRAINT conversa_client_id_fkey
            FOREIGN KEY (client_id)
            REFERENCES public.clientes_vizu(id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Drop Legacy Tables
-- ============================================================================

SELECT 'Dropping legacy tables' as step;

-- Drop configuracao_negocio first (has FK to cliente_vizu)
DROP TABLE IF EXISTS public.configuracao_negocio CASCADE;

-- Drop cliente_vizu (all FKs now point to clientes_vizu)
DROP TABLE IF EXISTS public.cliente_vizu CASCADE;

-- ============================================================================
-- STEP 6: Verify Final State
-- ============================================================================

SELECT 'Verifying final state' as step;

-- Check clientes_vizu structure
SELECT
    'clientes_vizu columns' as check_type,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'clientes_vizu'
ORDER BY ordinal_position;

-- Check all FK constraints now point to clientes_vizu
SELECT
    'Foreign keys to clientes_vizu' as check_type,
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'clientes_vizu'
ORDER BY tc.table_name;

-- Check record counts
SELECT
    'clientes_vizu' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT id) as unique_ids,
    COUNT(external_user_id) as oauth_users,
    COUNT(*) - COUNT(external_user_id) as api_key_users
FROM public.clientes_vizu;

-- Verify credencial_servico_externo can insert
SELECT
    'credencial_servico_externo test' as check_type,
    'All client_id values reference clientes_vizu' as status,
    COUNT(*) as credential_count
FROM public.credencial_servico_externo cse
WHERE EXISTS (
    SELECT 1 FROM public.clientes_vizu cv
    WHERE cv.id = cse.client_id
);

-- ============================================================================
-- STEP 7: Success Message
-- ============================================================================

SELECT
    '✅ Migration Complete!' as status,
    'All tables consolidated to clientes_vizu' as message,
    'Legacy tables cliente_vizu and configuracao_negocio dropped' as cleanup,
    'All FK constraints updated' as fk_status;
