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
- Use a protected GitHub Actions workflow (manual or gated) that runs `alembic upgrade head` against your production DB (Supabase). Store the DB URL as a secret (e.g., `SUPABASE_DB_URL`).
- The migration runner in the repository will only run `alembic upgrade head` (it will not autogenerate revisions).

Supabase deployment checklist
1. Create a Supabase project and obtain the Postgres connection string (use a restricted user with migration privileges).
2. Add any required Postgres extensions in Supabase (e.g., `pgcrypto`, `pgvector`) and include those SQL commands in a migration script if needed.
3. Add `SUPABASE_DB_URL` (or `DATABASE_URL`) to GitHub Secrets.
4. Run the migration workflow in a staging Supabase instance and validate.
5. Run the migration workflow against production Supabase (protected step).

Obsoleted patterns when migrating to Supabase
- `Base.metadata.create_all(...)` for schema creation in runtime: replace with Alembic migrations.
- Any ad-hoc runtime `alembic revision --autogenerate` performed in containers: stop generating in runtime and commit revisions in repo.
- Local-only ephemeral DB assumptions (ephemeral volumes without backups): move to managed Supabase.

Notes
- Keep migration files reviewed and stored in version control; review generated SQL in PRs before applying to production.
