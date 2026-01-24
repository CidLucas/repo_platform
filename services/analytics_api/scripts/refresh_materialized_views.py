#!/usr/bin/env python3
"""Refresh analytics_v2 materialized views by invoking the DB function.
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

def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        env_path = Path(__file__).resolve().parents[3] / '.env'
        database_url = load_database_url_from_dotenv(env_path)
    if not database_url:
        print('ERROR: DATABASE_URL not found in environment or .env', file=sys.stderr)
        sys.exit(2)

    try:
        import psycopg2
    except Exception as e:
        print('ERROR: psycopg2 is required to run this script:', e, file=sys.stderr)
        sys.exit(3)

    # Normalize SQLAlchemy-style DSN (e.g. postgresql+psycopg2://...) to libpq style
    if database_url.startswith('postgresql+psycopg2://'):
        database_url = database_url.replace('postgresql+psycopg2://', 'postgresql://', 1)

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            print('Attempting to call analytics_v2.refresh_materialized_views()...')
            try:
                cur.execute('SELECT analytics_v2.refresh_materialized_views();')
                try:
                    rows = cur.fetchall()
                    print('Function returned:', rows)
                except Exception:
                    print('Refresh function executed (no result set).')
            except Exception as e:
                print('Function call failed, falling back to explicit REFRESH statements:', e)
                views = [
                    'analytics_v2.mv_customer_summary',
                    'analytics_v2.mv_product_summary',
                    'analytics_v2.mv_monthly_sales_trend',
                ]
                for v in views:
                    try:
                        print(f'Refreshing {v}...')
                        cur.execute(f'REFRESH MATERIALIZED VIEW {v};')
                        print(f'Refreshed {v}')
                    except Exception as e2:
                        print(f'Failed to refresh {v}:', e2)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
