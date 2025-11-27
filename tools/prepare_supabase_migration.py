"""Prepare a SQL migration file for Supabase from the known Alembic DDL.

This script writes a SQL migration file `supabase_add_server_defaults.sql`
containing the statements to enable `pgcrypto` and set server-side defaults
for UUID and boolean columns. Use this file with the Supabase CLI:

  supabase link --project-ref <ref>
  supabase migration new add-server-defaults
  # copy contents of this file into the generated migration SQL
  supabase db push

The script also prints exact commands to run.
"""
from __future__ import annotations

import os
from datetime import datetime

SQL = '''-- supabase migration: add server defaults for cliente_vizu and configuracao_negocio
BEGIN;

-- Ensure pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Set server defaults for cliente_vizu
ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN api_key SET DEFAULT gen_random_uuid()::text;

-- Set boolean defaults for configuracao_negocio
ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_rag_habilitada SET DEFAULT false;
ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_sql_habilitada SET DEFAULT false;
ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_agendamento_habilitada SET DEFAULT false;

-- Enable Row Level Security (RLS) and example policies
-- NOTE: Service role bypasses RLS; policies below allow 'authenticated' users to select
-- and the service role to perform any action. Adjust policies to your security model.

ALTER TABLE IF EXISTS cliente_vizu ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "allow_service_role_all_cliente_vizu" ON cliente_vizu FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "allow_authenticated_select_cliente_vizu" ON cliente_vizu FOR SELECT
    USING (auth.role() = 'authenticated');

ALTER TABLE IF EXISTS configuracao_negocio ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "allow_service_role_all_configuracao" ON configuracao_negocio FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "allow_authenticated_select_configuracao" ON configuracao_negocio FOR SELECT
    USING (auth.role() = 'authenticated');

COMMIT;

-- Down (revert defaults and drop policies)
-- BEGIN;
-- ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN id DROP DEFAULT;
-- ALTER TABLE IF EXISTS cliente_vizu ALTER COLUMN api_key DROP DEFAULT;
-- ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_rag_habilitada DROP DEFAULT;
-- ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_sql_habilitada DROP DEFAULT;
-- ALTER TABLE IF EXISTS configuracao_negocio ALTER COLUMN ferramenta_agendamento_habilitada DROP DEFAULT;
-- DROP POLICY IF EXISTS "allow_service_role_all_cliente_vizu" ON cliente_vizu;
-- DROP POLICY IF EXISTS "allow_authenticated_select_cliente_vizu" ON cliente_vizu;
-- DROP POLICY IF EXISTS "allow_service_role_all_configuracao" ON configuracao_negocio;
-- DROP POLICY IF EXISTS "allow_authenticated_select_configuracao" ON configuracao_negocio;
-- COMMIT;
'''


def main() -> None:
    out_name = 'supabase_add_server_defaults.sql'
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    out_path = os.path.join(os.getcwd(), out_name)
    with open(out_path, 'w') as f:
        f.write(SQL)

    print(f"Wrote SQL migration to: {out_path}\n")
    print("Next steps (run on your machine with Supabase CLI installed):\n")
    print("1) Link project:\n   supabase link --project-ref <project-ref>\n")
    print("2) Create a new migration (this creates a folder and empty SQL file):\n   supabase migration new add-server-defaults\n")
    print("3) Open the generated SQL file and replace its contents with the contents of this file. Alternatively, copy this file into the generated migration folder.")
    print("4) Push migrations to Supabase:\n   supabase db push\n")


if __name__ == '__main__':
    main()
