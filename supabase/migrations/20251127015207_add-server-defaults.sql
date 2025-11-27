-- supabase migration: add server defaults for cliente_vizu and configuracao_negocio
BEGIN;

-- Ensure pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Set server defaults for cliente_vizu
ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN api_key SET DEFAULT gen_random_uuid()::text;

-- Set boolean defaults for configuracao_negocio
ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_rag_habilitada SET DEFAULT false;
ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_sql_habilitada SET DEFAULT false;
ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_agendamento_habilitada SET DEFAULT false;

-- Enable Row Level Security (RLS) and example policies
-- NOTE: Service role bypasses RLS; policies below allow 'authenticated' users to select
-- and the service role to perform any action. Adjust policies to your security model.

ALTER TABLE IF EXISTS cliente_vizu ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies p WHERE p.policyname = 'allow_service_role_all_cliente_vizu' AND p.tablename = 'cliente_vizu'
    ) THEN
        EXECUTE 'CREATE POLICY "allow_service_role_all_cliente_vizu" ON cliente_vizu FOR ALL USING (auth.role() = ''service_role'') WITH CHECK (auth.role() = ''service_role'')';
    END IF;
END$$;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies p WHERE p.policyname = 'allow_authenticated_select_cliente_vizu' AND p.tablename = 'cliente_vizu'
    ) THEN
        EXECUTE 'CREATE POLICY "allow_authenticated_select_cliente_vizu" ON cliente_vizu FOR SELECT USING (auth.role() = ''authenticated'')';
    END IF;
END$$;

ALTER TABLE IF EXISTS configuracao_negocio ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies p WHERE p.policyname = 'allow_service_role_all_configuracao' AND p.tablename = 'configuracao_negocio'
    ) THEN
        EXECUTE 'CREATE POLICY "allow_service_role_all_configuracao" ON configuracao_negocio FOR ALL USING (auth.role() = ''service_role'') WITH CHECK (auth.role() = ''service_role'')';
    END IF;
END$$;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies p WHERE p.policyname = 'allow_authenticated_select_configuracao' AND p.tablename = 'configuracao_negocio'
    ) THEN
        EXECUTE 'CREATE POLICY "allow_authenticated_select_configuracao" ON configuracao_negocio FOR SELECT USING (auth.role() = ''authenticated'')';
    END IF;
END$$;

COMMIT;

-- Down (revert defaults and drop policies)
-- BEGIN;
-- ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN id DROP DEFAULT;
-- ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN api_key DROP DEFAULT;
-- ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_rag_habilitada DROP DEFAULT;
-- ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_sql_habilitada DROP DEFAULT;
-- ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_agendamento_habilitada DROP DEFAULT;
-- DROP POLICY IF EXISTS "allow_service_role_all_cliente_vizu" ON cliente_vizu;
-- DROP POLICY IF EXISTS "allow_authenticated_select_cliente_vizu" ON cliente_vizu;
-- DROP POLICY IF EXISTS "allow_service_role_all_configuracao" ON configuracao_negocio;
-- DROP POLICY IF EXISTS "allow_authenticated_select_configuracao" ON configuracao_negocio;
-- COMMIT;
