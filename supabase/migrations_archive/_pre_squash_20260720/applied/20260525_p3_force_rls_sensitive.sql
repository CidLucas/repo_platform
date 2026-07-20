-- 20260525_p3_force_rls_sensitive.sql
-- P3: habilitar FORCE ROW LEVEL SECURITY em tabelas hipersensíveis.
-- Sem FORCE, o owner da tabela (postgres) bypassa RLS. Útil contra SECURITY DEFINER
-- functions mal configuradas e contra acesso direto via owner.
-- service_role (BYPASSRLS) continua bypassando independente de FORCE.

BEGIN;

ALTER TABLE public.integration_tokens FORCE ROW LEVEL SECURITY;
ALTER TABLE public.clientes_blu        FORCE ROW LEVEL SECURITY;
ALTER TABLE public.notifications       FORCE ROW LEVEL SECURITY;

-- Considerar futuramente:
-- ALTER TABLE public.messages FORCE ROW LEVEL SECURITY;
-- ALTER TABLE analytics_v2.fato_transacoes FORCE ROW LEVEL SECURITY;
-- (não incluídas aqui para limitar o blast radius do P3.)

COMMIT;
