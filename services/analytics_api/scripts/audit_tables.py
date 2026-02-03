#!/usr/bin/env python3
"""Audit analytics_v2 tables: counts, sample rows, null/zero percentages.

Usage:
  poetry run python services/analytics_api/scripts/audit_tables.py
"""
import os
import sys
from urllib.parse import urlparse

import pandas as pd
from sqlalchemy import create_engine, text


def get_db_engine():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # fallback to .env extraction
        here = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '..')
    return create_engine(database_url, pool_pre_ping=True)


def audit_table(engine, schema, table, sample_n=5):
    fq = f"{schema}.{table}"
    print(f"\n=== Audit: {fq} ===")

    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {fq}"))
        total_rows = int(total.scalar() or 0)
        print(f"Total rows: {total_rows}")

        # sample rows
        df_sample = pd.read_sql(text(f"SELECT * FROM {fq} LIMIT :n"), conn, params={'n': sample_n})
        print(f"\nSample rows (up to {sample_n}):")
        if df_sample.empty:
            print("  <no rows>")
        else:
            print(df_sample.head().to_string(index=False))

        # columns and types
        cols = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """), {'schema': schema, 'table': table}).fetchall()

        print('\nPer-column stats:')
        print('column | data_type | null_pct | zero_pct')

        for col_name, data_type in cols:
            # null count
            q = text(f"SELECT COUNT(*) as total, SUM(CASE WHEN {col_name} IS NULL THEN 1 ELSE 0 END) as nulls "
                     f"FROM {fq}")
            row = conn.execute(q).fetchone()
            total_cnt = int(row[0] or 0)
            nulls = int(row[1] or 0)
            null_pct = (nulls / total_cnt * 100) if total_cnt > 0 else 0.0

            zero_pct = None
            # check numeric-like types
            if data_type in ('integer','bigint','smallint','numeric','decimal','double precision','real'):
                qz = text(f"SELECT SUM(CASE WHEN {col_name} = 0 THEN 1 ELSE 0 END) as zeros FROM {fq}")
                rz = conn.execute(qz).fetchone()
                zeros = int(rz[0] or 0)
                zero_pct = (zeros / total_cnt * 100) if total_cnt > 0 else 0.0
            else:
                zero_pct = 'N/A'

            print(f"{col_name} | {data_type} | {null_pct:.2f}% | {zero_pct if zero_pct=='N/A' else f'{zero_pct:.2f}%'}")


if __name__ == '__main__':
    engine = get_db_engine()
    schema = 'analytics_v2'
    tables = ['dim_customer', 'dim_product']
    for t in tables:
        try:
            audit_table(engine, schema, t)
        except Exception as e:
            print(f"Failed auditing {schema}.{t}: {e}")
            sys.exit(1)

    print('\nAudit complete.')
