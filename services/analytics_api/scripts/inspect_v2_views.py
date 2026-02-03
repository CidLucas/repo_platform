#!/usr/bin/env python3
"""Inspect analytics_v2 reporting views: counts and sample rows.
"""
import os
import sys
from pathlib import Path


def load_env_value(key: str) -> str | None:
    p = Path('.').resolve() / '.env'
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.strip().startswith(f"{key}="):
            return line.split('=',1)[1].strip()
    return None

def get_db_url():
    url = os.environ.get('DATABASE_URL') or load_env_value('DATABASE_URL')
    if url and url.startswith('postgresql+psycopg2://'):
        url = url.replace('postgresql+psycopg2://','postgresql://',1)
    return url

def main():
    try:
        import psycopg2
    except Exception as e:
        print('ERROR: psycopg2 required -', e, file=sys.stderr)
        sys.exit(2)

    url = get_db_url()
    if not url:
        print('ERROR: DATABASE_URL not found in environment or .env', file=sys.stderr)
        sys.exit(3)

    client_id = os.environ.get('CLIENT_ID') or load_env_value('CLIENT_ID')

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    views = ['v_time_series', 'v_regional', 'v_last_orders', 'v_customer_products']
    for v in views:
        try:
            if client_id:
                cur.execute(f"SELECT COUNT(*) FROM analytics_v2.{v} WHERE client_id = %s", (client_id,))
            else:
                cur.execute(f"SELECT COUNT(*) FROM analytics_v2.{v}")
            cnt = cur.fetchone()[0]
            print(f"{v}: {cnt} rows")

            if client_id:
                cur.execute(f"SELECT * FROM analytics_v2.{v} WHERE client_id = %s LIMIT 5", (client_id,))
            else:
                cur.execute(f"SELECT * FROM analytics_v2.{v} LIMIT 5")
            rows = cur.fetchall()
            if cur.description:
                cols = [d[0] for d in cur.description]
                print('Sample columns:', cols)
                for r in rows:
                    print(dict(zip(cols, r)))
            else:
                print('No columns returned for', v)
        except Exception as e:
            print(f"Error querying {v}: {e}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
