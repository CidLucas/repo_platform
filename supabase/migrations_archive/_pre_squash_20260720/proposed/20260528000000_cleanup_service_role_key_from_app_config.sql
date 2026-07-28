-- SECURITY: Remove service_role_key de public.app_config (limpeza pós-auditoria)
--
-- A chave foi inserida por uma migration anterior. Com o dispatcher usando
-- exclusivamente vault.decrypted_secrets, não há mais razão para manter
-- segredos em tabela pública, mesmo com RLS ativo.
--
-- Contexto: Vault secret 'app_service_role_key' existe desde 2026-05-26.

BEGIN;

DELETE FROM public.app_config WHERE key = 'service_role_key';

-- Verifica que não sobrou nada
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.app_config WHERE key = 'service_role_key') THEN
    RAISE EXCEPTION 'service_role_key ainda presente em app_config após DELETE — abortar';
  END IF;
END $$;

COMMIT;
