#!/usr/bin/env python3
"""Check text columns for empty-string and literal 'NULL' values in target tables.
"""
import os
import sys
from pathlib import Path


def load_database_url_from_dotenv(dotenv_path: Path) -> str | None:
    if not dotenv_path.exists():
        return None
    with dotenv_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('DATABASE_URL='):
                return line.split('=', 1)[1]
    return None

def get_db_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        if url.startswith('postgresql+psycopg2://'):
            url = url.replace('postgresql+psycopg2://','postgresql://',1)
        return url
    env_path = Path(__file__).resolve().parents[3] / '.env'
    return load_database_url_from_dotenv(env_path)

def main():
    url = get_db_url()
    if not url:
        print('ERROR: DATABASE_URL not found in environment or .env', file=sys.stderr)
        sys.exit(2)
    try:
        import psycopg2
    except Exception as e:
        print('ERROR: psycopg2 required:', e, file=sys.stderr)
        sys.exit(3)

    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()

    tables = ['dim_customer', 'dim_product']
    schema = 'analytics_v2'
    results = {}
    for table in tables:
        cur.execute(
            """SELECT column_name, data_type FROM information_schema.columns
               WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position""",
            (schema, table),
        )
        cols = cur.fetchall()
        text_cols = [c for c,t in cols if t in ('text','character varying','varchar')]
        table_res = {}
        for col in text_cols:
            q = f"SELECT COUNT(*) FILTER (WHERE {col} = '') AS empty_count, COUNT(*) FILTER (WHERE {col} = 'NULL') AS literal_null_count FROM {schema}.{table};"
            try:
                cur.execute(q)
                empty_count, literal_null = cur.fetchone()
            except Exception as e:
                empty_count, literal_null = None, None
            table_res[col] = {'empty_count': empty_count, 'literal_NULL_count': literal_null}
        results[table] = table_res

    cur.close()
    conn.close()

    for table, cols in results.items():
        print(f"\n=== Text column empty/'NULL' counts for {schema}.{table} ===")
        if not cols:
            print('No text columns found')
            continue
        for col, stats in cols.items():
            print(f"{col}: empty_str={stats['empty_count']}, literal_NULL={stats['literal_NULL_count']}")

if __name__ == '__main__':
    main()
