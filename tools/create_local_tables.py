"""Create missing tables in the local Postgres using SQLModel metadata.

This is a helper to bring a fresh local DB up-to-date before running Alembic
revisions that expect tables to exist (useful during local development).

Usage:
  export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/vizu_db"
  python tools/create_local_tables.py
"""
from __future__ import annotations

import os
import sys

from sqlmodel import SQLModel, create_engine

def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: set DATABASE_URL environment variable", file=sys.stderr)
        sys.exit(1)

    # Ensure libs are importable when running from repo root
    # Import models package which registers tables on SQLModel.metadata
    try:
        import vizu_models  # noqa: F401
    except Exception as exc:
        print("Failed importing vizu_models:", exc, file=sys.stderr)
        sys.exit(1)

    engine = create_engine(db_url)
    print(f"Creating tables on {db_url}...")
    SQLModel.metadata.create_all(engine)
    print("Done.")


if __name__ == "__main__":
    main()
