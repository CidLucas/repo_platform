-- Drop any bq_ft_* / bq_pending_* foreign tables that accumulated in public
-- (uses pg_class relkind='f' since pg_tables excludes foreign tables)
DO $cleanup$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT n.nspname AS schema_name, c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'f'
      AND n.nspname = 'public'
      AND (c.relname LIKE 'bq_ft_%' OR c.relname LIKE 'bq_pending_%')
  LOOP
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I.%I CASCADE', r.schema_name, r.table_name);
    RAISE NOTICE 'Dropped foreign table %.%', r.schema_name, r.table_name;
  END LOOP;
END;
$cleanup$;
