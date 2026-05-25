-- 20260525_p0_fix_integration_tokens_rls.sql
-- P0 CRÍTICO: integration_tokens.SELECT vaza tokens quando JWT.sub é NULL.
-- Remove o ramo "sub IS NULL" da cláusula USING.
-- Service-role bypassa RLS por padrão, então Edge Functions continuam funcionando.

BEGIN;

DROP POLICY IF EXISTS "own client" ON public.integration_tokens;

CREATE POLICY "own client read"
ON public.integration_tokens
FOR SELECT
TO authenticated
USING (client_id = public.get_my_client_id());

-- Mantém a policy de DELETE existente intacta, mas renomeia para padronizar.
DROP POLICY IF EXISTS "own client delete" ON public.integration_tokens;

CREATE POLICY "own client delete"
ON public.integration_tokens
FOR DELETE
TO authenticated
USING (client_id = public.get_my_client_id());

COMMIT;

-- Validação pós-deploy:
--   SET role anon; SELECT count(*) FROM public.integration_tokens;  -- esperado: 0
--   SET role authenticated; ...com JWT do cliente A: só linhas do A.
