-- Squash da schema_migrations de produção para o baseline 20260720000000.
-- Reversível: restaure de schema_migrations_history_backup.sql se necessário.
BEGIN;
TRUNCATE supabase_migrations.schema_migrations;
INSERT INTO supabase_migrations.schema_migrations(version, name)
VALUES ('20260720000000', 'baseline');
SELECT version, name FROM supabase_migrations.schema_migrations;
COMMIT;
