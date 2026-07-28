-- 20260525_p1_integration_tokens_write_policies.sql
-- P1: explicitar policies de INSERT/UPDATE em integration_tokens.
-- Hoje não existem, então frontend authenticated não consegue gravar.
-- Service_role bypassa RLS, então Edge Functions seguem funcionando independentemente.
-- Este script torna o invariante "cliente só grava token do próprio client_id" explícito.

BEGIN;

DROP POLICY IF EXISTS "own client insert" ON public.integration_tokens;
DROP POLICY IF EXISTS "own client update" ON public.integration_tokens;

CREATE POLICY "own client insert"
ON public.integration_tokens
FOR INSERT
TO authenticated
WITH CHECK (client_id = public.get_my_client_id());

CREATE POLICY "own client update"
ON public.integration_tokens
FOR UPDATE
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

COMMIT;
