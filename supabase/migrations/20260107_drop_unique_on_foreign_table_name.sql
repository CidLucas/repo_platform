-- Migration: Drop unique constraint on foreign_table_name in bigquery_foreign_tables
-- Reason: Prevent duplicate key errors; uniqueness enforced via (client_id, table_name)

alter table if exists public.bigquery_foreign_tables
  drop constraint if exists bigquery_foreign_tables_foreign_table_name_key;
