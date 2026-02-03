"""Run Alembic migrations for the `vizu_db_connector` package (CI-friendly).

Features:
- Accepts `--db` to override `DATABASE_URL` environment variable.
- Optional `--sql-file <path>` to write the generated SQL instead of applying it.
- Ensures local `libs/vizu_models` and `libs/vizu_db_connector` sources are on
  `sys.path` so Alembic's `env.py` can import project models when run from CI or
  ephemeral containers.

Usage:
  export DATABASE_URL="postgresql+psycopg2://..."
  python run_migrations.py --db "$DATABASE_URL"

To generate SQL without applying (for Supabase or review):
  python run_migrations.py --db "$DATABASE_URL" --sql-file /tmp/migration.sql
"""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import redirect_stdout

from alembic.config import Config

from alembic import command


def locate_alembic_ini(start_path: str) -> str | None:
    """Locate `alembic.ini` relative to this file or parent directories."""
    candidates = [
        os.path.join(start_path, "alembic.ini"),
        os.path.join(start_path, "..", "alembic.ini"),
        os.path.join(start_path, "..", "..", "alembic.ini"),
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.exists(p):
            return p
    return None


def ensure_local_libs_on_path(repo_root: str) -> None:
    """Add local `libs/*/src` packages to sys.path so imports resolve during Alembic runs."""
    libs_dir = os.path.join(repo_root, "libs")
    if not os.path.isdir(libs_dir):
        return
    for child in os.listdir(libs_dir):
        src_path = os.path.join(libs_dir, child, "src")
        if os.path.isdir(src_path):
            if src_path not in sys.path:
                sys.path.insert(0, src_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Database URL to use (overrides env DATABASE_URL)")
    parser.add_argument(
        "--sql-file",
        help="If provided, write generated SQL to this file instead of applying",
    )
    args = parser.parse_args()

    db_url = args.db or os.getenv("DATABASE_URL")
    if not db_url:
        print(
            "Error: set DATABASE_URL environment variable or pass --db", file=sys.stderr
        )
        sys.exit(1)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    repo_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
    # Ensure local libs are importable for Alembic env imports
    ensure_local_libs_on_path(repo_root)

    alembic_ini = locate_alembic_ini(base_dir)
    if not alembic_ini:
        print(
            "Error: could not find alembic.ini (looked near package)", file=sys.stderr
        )
        sys.exit(1)

    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Ensure script_location points to the package alembic directory
    package_dir = os.path.dirname(alembic_ini)
    script_location = os.path.join(package_dir, "alembic")
    cfg.set_main_option("script_location", script_location)

    sql_file = args.sql_file
    if sql_file:
        # Write generated SQL to file by redirecting stdout while running alembic in SQL mode
        print(f"Generating SQL to: {sql_file}")
        with open(sql_file, "w", encoding="utf-8") as fh:
            with redirect_stdout(fh):
                command.upgrade(cfg, "head", sql=True)
        print("SQL generation complete")
    else:
        print(f"Applying migrations from {alembic_ini} -> {db_url}")
        command.upgrade(cfg, "head")


if __name__ == "__main__":
    main()
