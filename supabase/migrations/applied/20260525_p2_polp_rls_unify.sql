-- 20260525_p2_polp_rls_unify.sql
-- P2: padronizar policies polp_* para get_my_client_id() em vez de subquery em client_users.
-- Mantém o suporte multi-user via client_users adicionando OR no resolver, ou
-- alternativa: estender get_my_client_id() para considerar client_users (fora do escopo).
--
-- Decisão aqui: usar get_my_client_id() E manter fallback client_users para multi-user.
-- Adiciona INSERT/UPDATE/DELETE restritivos.

BEGIN;

-- Drop policies existentes
DROP POLICY IF EXISTS "client members read own polp accounts" ON public.polp_accounts;
DROP POLICY IF EXISTS "client members read own polp bills" ON public.polp_bills;
DROP POLICY IF EXISTS "client members read own polp integrations" ON public.polp_integrations;
DROP POLICY IF EXISTS "client members read own polp transactions" ON public.polp_transactions;

-- Helper inline: client_id pertence ao usuário (JWT claim OU membro em client_users)
-- Expressão repetida — extrair para função SQL stable se for escalar para mais tabelas.

-- polp_accounts
CREATE POLICY "own client read"
ON public.polp_accounts FOR SELECT TO authenticated
USING (
  client_id = public.get_my_client_id()
  OR client_id IN (SELECT client_id FROM public.client_users WHERE auth_user_id = auth.uid())
);

-- polp_bills
CREATE POLICY "own client read"
ON public.polp_bills FOR SELECT TO authenticated
USING (
  client_id = public.get_my_client_id()
  OR client_id IN (SELECT client_id FROM public.client_users WHERE auth_user_id = auth.uid())
);

-- polp_integrations
CREATE POLICY "own client read"
ON public.polp_integrations FOR SELECT TO authenticated
USING (
  client_id = public.get_my_client_id()
  OR client_id IN (SELECT client_id FROM public.client_users WHERE auth_user_id = auth.uid())
);

-- polp_transactions
CREATE POLICY "own client read"
ON public.polp_transactions FOR SELECT TO authenticated
USING (
  client_id = public.get_my_client_id()
  OR client_id IN (SELECT client_id FROM public.client_users WHERE auth_user_id = auth.uid())
);

-- Writes: bloqueadas para authenticated (continuam só via service_role do agent_api/edge).
-- Caso queiramos permitir writes do frontend, adicionar policies INSERT/UPDATE/DELETE
-- aqui replicando o mesmo USING/WITH CHECK.

COMMIT;
