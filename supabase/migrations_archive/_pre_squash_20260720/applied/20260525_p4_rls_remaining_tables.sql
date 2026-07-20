-- 20260525_p4_rls_remaining_tables.sql
-- P4: Endurecimento RLS das tabelas tenant-scoped não cobertas pelo Security Sprint.
-- Relatório: docs/security/rls-audit-mai2026.md
--
-- Mudanças:
--   1. Adiciona WITH CHECK em policies FOR ALL (analytics_v2.* + public.*)
--   2. Revoga grants amplos de anon/PUBLIC em writes
--   3. Recria policies polp_* com role=authenticated + cobertura INSERT/UPDATE/DELETE
--   4. Reforça frontend_events como write-only para authenticated
--
-- Idempotente: usa DROP POLICY IF EXISTS + CREATE POLICY, REVOKE IF EXISTS implícito.

BEGIN;

-- ============================================================================
-- 1. Policies FOR ALL — adicionar WITH CHECK
-- ============================================================================

-- analytics_v2.fato_transacoes
DROP POLICY IF EXISTS "own client" ON analytics_v2.fato_transacoes;
CREATE POLICY "own client"
ON analytics_v2.fato_transacoes
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- analytics_v2.dim_inventory
DROP POLICY IF EXISTS "own client" ON analytics_v2.dim_inventory;
CREATE POLICY "own client"
ON analytics_v2.dim_inventory
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- analytics_v2.dim_clientes
DROP POLICY IF EXISTS "own client" ON analytics_v2.dim_clientes;
CREATE POLICY "own client"
ON analytics_v2.dim_clientes
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- analytics_v2.dim_fornecedores
DROP POLICY IF EXISTS "own client" ON analytics_v2.dim_fornecedores;
CREATE POLICY "own client"
ON analytics_v2.dim_fornecedores
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- public.approval_requests
DROP POLICY IF EXISTS "own client" ON public.approval_requests;
CREATE POLICY "own client"
ON public.approval_requests
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- public.client_insights
DROP POLICY IF EXISTS "own client" ON public.client_insights;
CREATE POLICY "own client"
ON public.client_insights
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- public.client_routines
DROP POLICY IF EXISTS "own client" ON public.client_routines;
CREATE POLICY "own client"
ON public.client_routines
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- public.messages
DROP POLICY IF EXISTS "own client" ON public.messages;
CREATE POLICY "own client"
ON public.messages
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- public.standalone_agent_sessions
DROP POLICY IF EXISTS "own client" ON public.standalone_agent_sessions;
CREATE POLICY "own client"
ON public.standalone_agent_sessions
FOR ALL
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- ============================================================================
-- 2. Revogar grants amplos de anon e PUBLIC em public.*
-- ============================================================================
-- Padrão (mesmo aplicado em integration_tokens / notifications / clientes_blu):
--   - anon: revogar tudo (sem casos de uso legítimos)
--   - PUBLIC: revogar writes (mantém SELECT se a tabela tem leitura pública por design)
--   - authenticated/service_role: preservados (RLS faz a defesa fina)

REVOKE ALL ON public.approval_requests          FROM anon, PUBLIC;
REVOKE ALL ON public.client_insights            FROM anon, PUBLIC;
REVOKE ALL ON public.client_routines            FROM anon, PUBLIC;
REVOKE ALL ON public.messages                   FROM anon, PUBLIC;
REVOKE ALL ON public.standalone_agent_sessions  FROM anon, PUBLIC;
REVOKE ALL ON public.frontend_events            FROM anon, PUBLIC;
REVOKE ALL ON public.polp_integrations          FROM anon, PUBLIC;
REVOKE ALL ON public.polp_accounts              FROM anon, PUBLIC;
REVOKE ALL ON public.polp_transactions          FROM anon, PUBLIC;
REVOKE ALL ON public.polp_bills                 FROM anon, PUBLIC;

-- Reconcede só o que authenticated precisa
GRANT SELECT, INSERT, UPDATE, DELETE ON public.approval_requests          TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.client_insights            TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.client_routines            TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.messages                   TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.standalone_agent_sessions  TO authenticated;
-- frontend_events: write-only (sem SELECT a authenticated)
GRANT INSERT ON public.frontend_events                                    TO authenticated;
-- polp_*: leitura via app, writes só service_role
GRANT SELECT ON public.polp_integrations  TO authenticated;
GRANT SELECT ON public.polp_accounts      TO authenticated;
GRANT SELECT ON public.polp_transactions  TO authenticated;
GRANT SELECT ON public.polp_bills         TO authenticated;

-- ============================================================================
-- 3. polp_* — policies recriadas (authenticated + cobertura completa)
-- ============================================================================

-- polp_integrations
DROP POLICY IF EXISTS "client members read own polp integrations" ON public.polp_integrations;
DROP POLICY IF EXISTS "polp_integrations: own client read"        ON public.polp_integrations;
CREATE POLICY "polp_integrations: own client read"
ON public.polp_integrations
FOR SELECT
TO authenticated
USING (
  client_id IN (
    SELECT client_users.client_id FROM client_users
    WHERE client_users.auth_user_id = auth.uid()
  )
  OR client_id = public.get_my_client_id()
);

-- polp_accounts
DROP POLICY IF EXISTS "client members read own polp accounts" ON public.polp_accounts;
DROP POLICY IF EXISTS "polp_accounts: own client read"        ON public.polp_accounts;
CREATE POLICY "polp_accounts: own client read"
ON public.polp_accounts
FOR SELECT
TO authenticated
USING (
  client_id IN (
    SELECT client_users.client_id FROM client_users
    WHERE client_users.auth_user_id = auth.uid()
  )
  OR client_id = public.get_my_client_id()
);

-- polp_transactions
DROP POLICY IF EXISTS "client members read own polp transactions" ON public.polp_transactions;
DROP POLICY IF EXISTS "polp_transactions: own client read"        ON public.polp_transactions;
CREATE POLICY "polp_transactions: own client read"
ON public.polp_transactions
FOR SELECT
TO authenticated
USING (
  client_id IN (
    SELECT client_users.client_id FROM client_users
    WHERE client_users.auth_user_id = auth.uid()
  )
  OR client_id = public.get_my_client_id()
);

-- polp_bills
DROP POLICY IF EXISTS "client members read own polp bills" ON public.polp_bills;
DROP POLICY IF EXISTS "polp_bills: own client read"        ON public.polp_bills;
CREATE POLICY "polp_bills: own client read"
ON public.polp_bills
FOR SELECT
TO authenticated
USING (
  client_id IN (
    SELECT client_users.client_id FROM client_users
    WHERE client_users.auth_user_id = auth.uid()
  )
  OR client_id = public.get_my_client_id()
);

-- Writes em polp_* permanecem sem policy (só service_role pode escrever, bypass RLS).
-- Isso é intencional: ingestão é 100% backend (sync_polp_transactions / edge fns).

-- ============================================================================
-- 4. frontend_events — manter policy INSERT, sem SELECT/UPDATE/DELETE policies
-- ============================================================================
-- A ausência de policy SELECT bloqueia leitura por authenticated (RLS deny-by-default).
-- Backend usa service_role para analytics. Comportamento já correto; só reforçamos
-- a policy de insert para garantir WITH CHECK.

DROP POLICY IF EXISTS "own client" ON public.frontend_events;
CREATE POLICY "own client insert"
ON public.frontend_events
FOR INSERT
TO authenticated
WITH CHECK (client_id = public.get_my_client_id());

COMMIT;

-- ============================================================================
-- Verificação pós-aplicação (rodar manualmente após COMMIT):
-- ============================================================================
-- SELECT schemaname, tablename, policyname, roles, cmd, with_check
-- FROM pg_policies
-- WHERE schemaname IN ('public','analytics_v2')
--   AND tablename IN ('fato_transacoes','dim_inventory','dim_clientes','dim_fornecedores',
--                     'approval_requests','client_insights','client_routines','messages',
--                     'standalone_agent_sessions','frontend_events',
--                     'polp_integrations','polp_accounts','polp_transactions','polp_bills')
-- ORDER BY schemaname, tablename, cmd;
--
-- Esperado: todas as policies FOR ALL com with_check preenchido; polp_* com role=authenticated.
