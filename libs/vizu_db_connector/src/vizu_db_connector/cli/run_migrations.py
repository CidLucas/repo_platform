"""Run Alembic migrations for the `vizu_db_connector` package.

This helper locates the package `alembic.ini` and runs `alembic upgrade head`
against the `DATABASE_URL` environment variable provided. It is safe to use
against local Postgres or a Supabase DB (set `DATABASE_URL` accordingly).

Usage (zsh):
  export DATABASE_URL="postgresql+psycopg2://user:pw@host:5432/dbname?sslmode=require"
  python tools/run_migrations.py

You can also pass an explicit DB URL:
  python tools/run_migrations.py --db "postgresql://..."
"""

from __future__ import annotations

import argparse
import os
import sys

from alembic import command
from alembic.config import Config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Database URL to use (overrides env DATABASE_URL)")
    args = parser.parse_args()

    db_url = args.db or os.getenv("DATABASE_URL")
    if not db_url:
        print(
            "Error: set DATABASE_URL environment variable or pass --db", file=sys.stderr
        )
        sys.exit(1)

    # Build path to the alembic.ini inside the vizu_db_connector package
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini = os.path.join(repo_root, "libs", "vizu_db_connector", "alembic.ini")
    if not os.path.exists(alembic_ini):
        print(f"Error: could not find alembic.ini at {alembic_ini}", file=sys.stderr)
        sys.exit(1)

    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", db_url)
    # Ensure Alembic script_location is absolute (points to the package alembic dir)
    package_dir = os.path.dirname(alembic_ini)
    script_location = os.path.join(package_dir, "alembic")
    cfg.set_main_option("script_location", script_location)

    print(f"Running migrations from {alembic_ini} -> {db_url}")
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    main()
