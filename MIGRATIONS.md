# Migrations workflow

This document explains how to generate, commit, and apply Alembic migrations for the monorepo.

Goals
- Keep schema changes explicit and versioned in `libs/vizu_db_connector/alembic/versions/`.
- Avoid generating revision files at runtime in containers or CI.
- Provide a safe workflow to apply migrations to staging/production (e.g., Supabase).

Local developer workflow
1. Ensure dependencies are installed for `vizu_models` and `vizu_db_connector`. From repo root:

```bash
cd libs/vizu_db_connector
poetry install
```

2. Point `DATABASE_URL` to a local/dev Postgres (do NOT target production):

```bash
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/vizu_db_dev
```

3. Create an Alembic revision (autogenerate), inspect and edit the file, then commit it:

```bash
poetry run alembic revision --autogenerate -m "add my change"
# inspect and adjust `libs/vizu_db_connector/alembic/versions/<rev>_*.py`
git add libs/vizu_db_connector/alembic/versions/<rev>_*.py
git commit -m "alembic: add <desc>"
```

4. Apply the migration locally to verify:

```bash
# from repo root
docker compose run --rm migration_runner python main.py
# or run alembic directly from libs/vizu_db_connector if preferred
```

CI / Protected apply
- Do NOT run `alembic upgrade head` directly against Supabase from CI. Supabase expects an SQL migration to be applied (for audit and review) — the safe flow is to generate the SQL from your Alembic revision and then apply that SQL to Supabase using one of the supported mechanisms (psql, Supabase Dashboard SQL editor, or the Supabase CLI).

- Recommended protected apply workflow (high level):
	1. Generate the SQL for the target migration locally or in a controlled runner: from `libs/vizu_db_connector` run `alembic upgrade head --sql > /tmp/migration.sql` (or run the same command from the repo root pointing to the alembic.ini). This emits the raw SQL that Alembic would run.
	2. Review the generated `/tmp/migration.sql` carefully in a PR or by hand — confirm extension creation, grants, or destructive operations.
	3. Apply the SQL to Supabase using one of the options below inside a protected/manual CI job (or via the Supabase dashboard):
		 - Run `psql "$SUPABASE_DB_URL" -f /tmp/migration.sql` from a runner that has network access to Supabase (recommended when automating in CI). Use `PGPASSWORD` or a connection string with credentials stored in a secret.
		 - Paste and run the SQL in the Supabase project's SQL editor in the dashboard (manual, interactive review).
		 - Use the `supabase` CLI migrations tooling if you maintain a Supabase-style migrations folder and workflow (see Supabase docs for `supabase db push` / migration workflows).

	Note: whichever mechanism you choose, keep the generated SQL file as the auditable artifact and ensure the protected CI job requires human review/approval before executing against production.

Supabase deployment checklist
1. Create a Supabase project and obtain the Postgres connection string (use a restricted user with migration privileges).
2. Add any required Postgres extensions in Supabase (e.g., `pgcrypto`, `pgvector`) and include those SQL commands in a migration script if needed.
3. Add `SUPABASE_DB_URL` (or `DATABASE_URL`) to GitHub Secrets.
4. Generate the SQL for your migration (`alembic upgrade head --sql > migration.sql`), validate it in staging, and keep the SQL file as the reviewed artifact.
5. Apply the SQL to production only from a protected/manual workflow (via `psql "$SUPABASE_DB_URL" -f migration.sql`, the Supabase dashboard SQL editor, or the `supabase` CLI), after human review and approval.

Obsoleted patterns when migrating to Supabase
- `Base.metadata.create_all(...)` for schema creation in runtime: replace with Alembic migrations.
- Any ad-hoc runtime `alembic revision --autogenerate` performed in containers: stop generating in runtime and commit revisions in repo.
- Local-only ephemeral DB assumptions (ephemeral volumes without backups): move to managed Supabase.

Notes
- Keep migration files reviewed and stored in version control; review generated SQL in PRs before applying to production.

Run migrations from the Makefile (local env)
-----------------------------------------

If you want to run the migration runner from your host environment (without Docker), use the `migrate-local` Makefile target. It exports `PYTHONPATH` so `vizu_models` and `vizu_db_connector` are importable from the checked-out repo.

Example (recommended when you're in a venv / have deps installed):

```bash
# from repo root
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/vizu_db make migrate-local
```

If you prefer to install the local libs into your current Python environment instead of setting `PYTHONPATH`, run:

```bash
make migrate-local-install
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/vizu_db make migrate-local
```

Notes:
- `migrate-local` expects `DATABASE_URL` to be set (it will abort if unset).
- Use a Python virtualenv or Poetry-managed environment to avoid polluting your system Python.
