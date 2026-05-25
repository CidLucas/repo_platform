-- 20260525_p2_normalize_roles_to_authenticated.sql
-- P2: substituir role "public" por "authenticated" em policies tenant-scoped.
-- public inclui anon — semanticamente errado para dados de tenant.
-- Service_role bypassa RLS independente da role da policy.
--
-- Tabelas atingidas: bigquery_foreign_tables, client_routine_executions, clientes_blu.
-- (notifications, integration_tokens, polp_* já são tratadas em outras migrations P0/P1/P2.)

BEGIN;

-- bigquery_foreign_tables (3 policies)
DROP POLICY IF EXISTS bigquery_foreign_tables_access ON public.bigquery_foreign_tables;
DROP POLICY IF EXISTS bigquery_foreign_tables_update ON public.bigquery_foreign_tables;
DROP POLICY IF EXISTS bigquery_foreign_tables_write ON public.bigquery_foreign_tables;

-- Mantém o bypass de service_role explícito (defensivo) + check para authenticated.
CREATE POLICY bigquery_foreign_tables_select
ON public.bigquery_foreign_tables FOR SELECT TO authenticated
USING (client_id = public.get_my_client_id());

CREATE POLICY bigquery_foreign_tables_insert
ON public.bigquery_foreign_tables FOR INSERT TO authenticated
WITH CHECK (client_id = public.get_my_client_id());

CREATE POLICY bigquery_foreign_tables_update
ON public.bigquery_foreign_tables FOR UPDATE TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

CREATE POLICY bigquery_foreign_tables_delete
ON public.bigquery_foreign_tables FOR DELETE TO authenticated
USING (client_id = public.get_my_client_id());

-- client_routine_executions: tinha SELECT em public; mover para authenticated.
DROP POLICY IF EXISTS "own client" ON public.client_routine_executions;
CREATE POLICY "own client read"
ON public.client_routine_executions FOR SELECT TO authenticated
USING (client_id = public.get_my_client_id());

-- clientes_blu: 4 policies em public — recriar 3 em authenticated, manter service_role como bypass.
DROP POLICY IF EXISTS "Authenticated users insert own" ON public.clientes_blu;
DROP POLICY IF EXISTS "Authenticated users read own" ON public.clientes_blu;
DROP POLICY IF EXISTS "Authenticated users update own" ON public.clientes_blu;
DROP POLICY IF EXISTS "Service role unrestricted" ON public.clientes_blu;

CREATE POLICY "authenticated read own"
ON public.clientes_blu FOR SELECT TO authenticated
USING (external_user_id = (auth.jwt() ->> 'sub'));

CREATE POLICY "authenticated insert own"
ON public.clientes_blu FOR INSERT TO authenticated
WITH CHECK (external_user_id = (auth.jwt() ->> 'sub'));

CREATE POLICY "authenticated update own"
ON public.clientes_blu FOR UPDATE TO authenticated
USING (external_user_id = (auth.jwt() ->> 'sub'))
WITH CHECK (external_user_id = (auth.jwt() ->> 'sub'));

-- service_role já bypassa RLS pelo grant default da Supabase; policy redundante removida.
-- Caso queiramos restaurar a policy explícita por motivos de auditoria, descomentar:
-- CREATE POLICY "service_role unrestricted"
--   ON public.clientes_blu FOR ALL TO service_role
--   USING (true) WITH CHECK (true);

COMMIT;
