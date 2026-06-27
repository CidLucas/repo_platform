-- ============================================================
-- Wipe all test clients and auth users
-- Date: 2026-06-27
--
-- ⚠️  DESTRUCTIVE. Run only against a dev/test project.
-- Will cascade-delete all rows in tables that reference
-- clientes_blu (see list below).
--
-- Tables affected by CASCADE when clientes_blu is deleted:
--   approval_requests, bigquery_foreign_tables, bigquery_servers,
--   calendar_settings, calendar_watch_channels, client_approval_rules,
--   client_approval_stats, client_data_sources, client_dimension_kpis,
--   client_enabled_agents, client_goals, client_insights,
--   client_knowledge_documents, client_notification_preferences,
--   client_routine_executions, client_routines, client_users,
--   conversa, credencial_servico_externo, dimension_state,
--   doc_templates, documents, frontend_events, integration_configs,
--   integration_tokens, messages, and ~30 more.
--
-- To run:
--   1. Supabase Dashboard → SQL Editor → New query
--   2. Paste this file
--   3. Click "Run" (or Cmd/Ctrl + Enter)
--   4. Confirm the "BEFORE" counts, then uncomment the DELETE
--      statements and run again
-- ============================================================

-- ── 1. BEFORE counts (run this first to see what will be deleted) ─────────
select
  (select count(*) from public.clientes_blu)  as clientes_blu_rows,
  (select count(*) from auth.users)           as auth_users_rows,
  (select count(*) from auth.identities)      as auth_identities_rows,
  (select count(*) from auth.sessions)        as auth_sessions_rows;

-- ── 2. WIPE — uncomment and run AFTER you've reviewed the counts ──────────
--
-- delete from auth.users;       -- CASCADEs to identities, sessions, refresh_tokens
-- delete from public.clientes_blu;  -- CASCADEs to ~30 dependent tables
--
-- ── 3. AFTER counts (should all be 0) ─────────────────────────────────────
--
-- select
--   (select count(*) from public.clientes_blu)  as clientes_blu_rows,
--   (select count(*) from auth.users)           as auth_users_rows,
--   (select count(*) from auth.identities)      as auth_identities_rows;
