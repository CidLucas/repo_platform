-- ============================================================================
-- Fix: Change credencial_servico_externo FK from cliente_vizu to clientes_vizu
-- Issue: Google OAuth users are in clientes_vizu, but FK points to cliente_vizu
-- Copy and paste this entire file into Supabase SQL Editor and click Run
-- ============================================================================

-- Step 1: Check current state
SELECT
    'credencial_servico_externo foreign keys' as check_type,
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
  AND tc.table_name='credencial_servico_externo';

-- Step 2: Check if we have any existing credentials (need to preserve data)
SELECT
    'existing_credentials' as check_type,
    COUNT(*) as total_credentials,
    COUNT(DISTINCT client_id) as unique_clients
FROM public.credencial_servico_externo;

-- Step 3: Check which table has your user
-- (Replace 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723' with your actual client_id)
SELECT 'User in cliente_vizu (old table)' as check_type, COUNT(*) as found
FROM public.cliente_vizu
WHERE id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
UNION ALL
SELECT 'User in clientes_vizu (new table)' as check_type, COUNT(*) as found
FROM public.clientes_vizu
WHERE id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';

-- Step 4: Drop the old FK constraint
-- (Get the exact constraint name from Step 1 result, usually something like credencial_servico_externo_client_id_fkey)
ALTER TABLE public.credencial_servico_externo
DROP CONSTRAINT IF EXISTS credencial_servico_externo_client_id_fkey;

-- Step 5: Add the new FK constraint pointing to clientes_vizu
ALTER TABLE public.credencial_servico_externo
ADD CONSTRAINT credencial_servico_externo_client_id_fkey
FOREIGN KEY (client_id)
REFERENCES public.clientes_vizu(id)
ON DELETE CASCADE;

-- Step 6: Verify the new FK constraint
SELECT
    'credencial_servico_externo foreign keys (AFTER FIX)' as check_type,
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
  AND tc.table_name='credencial_servico_externo';

-- Step 7: Test insert (optional - comment out if you don't want to test)
-- This should now work if your user exists in clientes_vizu
-- INSERT INTO public.credencial_servico_externo (
--     client_id,
--     nome_servico,
--     tipo_servico,
--     credenciais_cifradas,
--     status
-- ) VALUES (
--     'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
--     'Test Connection',
--     'BIGQUERY',
--     '{"test": "data"}',
--     'pending'
-- );

-- Step 8: Show final table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'credencial_servico_externo'
ORDER BY ordinal_position;
