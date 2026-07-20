-- 20260525_p1_fix_notifications_rls.sql
-- P1: notifications usa claim raiz `client_id` que JWTs Supabase não populam.
-- Padroniza para get_my_client_id() e adiciona INSERT/DELETE controlados.

BEGIN;

DROP POLICY IF EXISTS "notifications: client sees own" ON public.notifications;
DROP POLICY IF EXISTS "notifications: client updates own" ON public.notifications;

CREATE POLICY "own client read"
ON public.notifications
FOR SELECT
TO authenticated
USING (client_id = public.get_my_client_id());

CREATE POLICY "own client update"
ON public.notifications
FOR UPDATE
TO authenticated
USING (client_id = public.get_my_client_id())
WITH CHECK (client_id = public.get_my_client_id());

-- INSERT geralmente vem do service_role (agent_api). Mantemos uma policy
-- restritiva para o caso de algum fluxo authenticated criar notificação.
CREATE POLICY "own client insert"
ON public.notifications
FOR INSERT
TO authenticated
WITH CHECK (client_id = public.get_my_client_id());

CREATE POLICY "own client delete"
ON public.notifications
FOR DELETE
TO authenticated
USING (client_id = public.get_my_client_id());

COMMIT;
