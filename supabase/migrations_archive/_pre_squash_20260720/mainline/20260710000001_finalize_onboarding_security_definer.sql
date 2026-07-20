-- finalize_onboarding roda como `authenticated`, mas dispatch_routine_event()
-- só concede EXECUTE a postgres/service_role — o SELECT dispatch_routine_event(...)
-- dava permission denied, engolido pelo EXCEPTION WHEN OTHERS: nenhum onboarding
-- disparava a rotina onboarding_complete (routine_execution_id sempre null).
--
-- SECURITY DEFINER é seguro aqui: o client_id vem de get_my_client_id() (JWT do
-- caller), nunca de parâmetro — um usuário não consegue despachar evento para
-- outro client. search_path já está pinado em 'public, pg_temp' na função.
--
-- APLICADA em prod via psql em 2026-07-10 (registrada manualmente em
-- supabase_migrations.schema_migrations — prod tem drift, não usar db push).

ALTER FUNCTION public.finalize_onboarding() SECURITY DEFINER;
