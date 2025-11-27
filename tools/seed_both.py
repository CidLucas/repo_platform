"""Seed both local (TEST_DATABASE_URL) and Supabase (DATABASE_URL).

Usage:
  # use env vars (recommended)
  export TEST_DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/vizu_db_test"
  export DATABASE_URL="postgresql+psycopg2://user:password@host:5432/postgres?sslmode=require"
  poetry run python tools/seed_both.py

Optional flags:
  --create-tables    Create missing tables from SQLModel metadata before inserting.

This script uses the canonical model classes from `vizu_models` and inserts
the same seed records into both target databases. It intentionally avoids
calling the HTTP APIs so you can seed the DBs directly.
"""
from __future__ import annotations
from os import getenv
import os
import argparse
import uuid
from typing import List

from sqlmodel import SQLModel, Session, create_engine
from vizu_models import (
    ClienteVizu,
    ClienteVizuCreate,
    ConfiguracaoNegocio,
    TipoCliente,
    TierCliente,
)

test_db = "postgresql+psycopg2://user:password@localhost:5432/vizu_db"
supa_db = "postgresql+psycopg2://postgres:tMz1us7KsAHQs6QT@db.haruewffnubdgyofftut.supabase.co:5432/postgres"



SEED_CLIENTS = [
    {"nome_empresa": "Oficina Mendes"},
    {"nome_empresa": "Studio J"},
    {"nome_empresa": "Casa com Alma"},
    {"nome_empresa": "Consultório Odontológico Dra. Beatriz Almeida"},
    {"nome_empresa": "Marcos Eletricista"},
]


def seed_db(database_url: str, create_tables: bool = False) -> List[uuid.UUID]:
    print(f"Seeding database: {database_url}")
    engine = create_engine(database_url, echo=False)

    if create_tables:
        print("Creating tables from SQLModel metadata (if missing)...")
        SQLModel.metadata.create_all(engine)

    ids: List[uuid.UUID] = []
    with Session(engine) as session:
        for item in SEED_CLIENTS:
            cliente = ClienteVizu(
                nome_empresa=item["nome_empresa"],
                tipo_cliente=TipoCliente.EXTERNO,
                tier=TierCliente.SME,
            )
            session.add(cliente)
            session.commit()
            session.refresh(cliente)
            ids.append(cliente.id)

            # create a minimal ConfiguracaoNegocio linked to the cliente
            try:
                cfg = ConfiguracaoNegocio(
                    cliente_vizu_id=cliente.id,
                    prompt_base=f"Contexto padrão para {cliente.nome_empresa}",
                    ferramenta_rag_habilitada=False,
                )
                session.add(cfg)
                session.commit()
            except Exception:
                # Some deployments may have different ConfiguracaoNegocio fields;
                # ignore config insertion errors but keep the client created.
                session.rollback()
        print(f"Inserted {len(SEED_CLIENTS)} clients into {database_url}")

    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-tables", action="store_true", help="Create tables from metadata before inserting")
    args = parser.parse_args()

    if not test_db and not supa_db:
        print("Error: neither TEST_DATABASE_URL nor DATABASE_URL is set in the environment.")
        print("Set them and rerun. Example (zsh):")
        print("export TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/vizu_db_test")
        print("export DATABASE_URL=postgresql+psycopg2://user:pw@host:5432/postgres?sslmode=require")
        raise SystemExit(1)

    results = {}
    if test_db:
        try:
            results["test"] = seed_db(test_db, create_tables=args.create_tables)
        except Exception as exc:
            print(f"Failed seeding TEST database: {exc}")

    if supa_db:
        try:
            results["supabase"] = seed_db(supa_db, create_tables=args.create_tables)
        except Exception as exc:
            print(f"Failed seeding Supabase database: {exc}")

    print("Seeding complete. Summary:")
    for k, v in results.items():
        print(f" - {k}: {len(v)} clients inserted")


if __name__ == "__main__":
    main()
