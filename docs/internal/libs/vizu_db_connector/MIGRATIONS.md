**Migrations**

- **Location:** `libs/vizu_db_connector/alembic`
- Alembic configuration file: `libs/vizu_db_connector/alembic.ini`
- Migration scripts live in: `libs/vizu_db_connector/alembic/versions/`

How to run migrations locally or against Supabase

1. Locally (using the repo helper):

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/vizu_db"
python tools/run_migrations.py
```

2. Against Supabase (use the service-role key and SSL):

```bash
export DATABASE_URL="postgresql+psycopg2://postgres:<password>@<host>:5432/postgres?sslmode=require"
python tools/run_migrations.py
```

Notes
- Migrations are stored inside `libs/vizu_db_connector` to keep DB schema centralized.
- Services should set `DATABASE_URL` to point to the desired environment (local or Supabase).
- The repository includes a migration that sets server-side defaults for UUID columns
  (`gen_random_uuid()`) and boolean flags to make client inserts idempotent and simpler.

Security
- Do not commit secrets. Use `.env` files locally (keep them out of git) or GitHub
  Actions Secrets for CI. The `tools/run_migrations.py` helper reads `DATABASE_URL` from
  the environment.

Supabase-specific flow
----------------------

Supabase recommends using their CLI to manage and push migrations (`supabase migration` / `supabase db push`). To make this repo compatible with that flow we provide a helper that prepares a SQL migration file you can use with the Supabase CLI.

1. Prepare SQL migration locally (already provided):

```bash
python tools/prepare_supabase_migration.py
```

This writes `supabase_add_server_defaults.sql` in the repo root. It contains the same DDL as the Alembic migration that sets `pgcrypto` and server defaults.

2. Use the Supabase CLI on your machine:

```bash
supabase link --project-ref <your-project-ref>
supabase migration new add-server-defaults
# copy contents of supabase_add_server_defaults.sql into the migration file created by the previous command
supabase db push
```

3. After push completes, your Supabase database will have the server-side defaults and future inserts can omit `id`/`api_key` and boolean flags.

Notes
- The repo still keeps Alembic migrations for local & CI workflows. The Supabase flow uses raw SQL migration files pushed with the Supabase CLI.
- If you want, I can automate the step that copies the prepared SQL into the CLI-generated migration folder, but it requires running `supabase` locally (which requires auth and the CLI installed).

