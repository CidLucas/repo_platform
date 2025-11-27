"""Run Alembic migrations for the `vizu_db_connector` package (CI-friendly).

Usage:
  export DATABASE_URL="postgresql+psycopg2://..."
  python run_migrations.py

This script is intended to live inside `libs/vizu_db_connector` so CI can
`cd` into the folder, run `poetry install` and then `poetry run python run_migrations.py`.
"""
from __future__ import annotations

import os
import sys
import argparse
from alembic.config import Config
from alembic import command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Database URL to use (overrides env DATABASE_URL)")
    args = parser.parse_args()

    db_url = args.db or os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: set DATABASE_URL environment variable or pass --db", file=sys.stderr)
        sys.exit(1)

    # Alembic ini lives in this package folder
    base_dir = os.path.abspath(os.path.dirname(__file__))
    alembic_ini = os.path.join(base_dir, "alembic.ini")
    if not os.path.exists(alembic_ini):
        # Try parent folder (if run from src path)
        alembic_ini = os.path.join(base_dir, "..", "alembic.ini")
        alembic_ini = os.path.abspath(alembic_ini)
    if not os.path.exists(alembic_ini):
        print(f"Error: could not find alembic.ini (looked at {alembic_ini})", file=sys.stderr)
        sys.exit(1)

    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", db_url)
    # Ensure script_location points to the package alembic directory
    package_dir = os.path.dirname(alembic_ini)
    script_location = os.path.join(package_dir, "alembic")
    cfg.set_main_option("script_location", script_location)

    print(f"Running migrations from {alembic_ini} -> {db_url}")
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    main()
