#!/usr/bin/env python3
"""
ETL Script to load ONLY fact_sales in small batches.
Assumes dimensions (dim_customer, dim_supplier, dim_product) are already loaded.

Usage:
    cd services/analytics_api
    export DATABASE_URL="postgresql://..."
    poetry run python src/analytics_api/services/etl_fact_sales_only.py
"""
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from analytics_api.data_access.postgres_repository import PostgresRepository

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent / "product_invoices (1).csv"
TEST_CLIENT_ID = "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
BATCH_SIZE = 10000  # Process 10k rows at a time

COLUMN_MAPPING = {
    "id_operatorinvoice": "order_id",
    "emittedat_operatorinvoice": "data_transacao",
    "emitterlegalname": "emitter_nome",
    "emitterlegaldoc": "emitter_cnpj",
    "receiverlegalname": "receiver_nome",
    "receiverlegaldoc": "receiver_cpf_cnpj",
    "description_product": "raw_product_description",
    "quantitytraded_product": "quantidade",
    "unitprice_product": "valor_unitario",
    "totalprice_product": "valor_total_emitter",
}


def load_csv() -> pd.DataFrame:
    """Load and transform CSV."""
    logger.info(f"Loading CSV from: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)

    rename_map = {src: tgt for src, tgt in COLUMN_MAPPING.items() if src in df.columns}
    df = df.rename(columns=rename_map)

    if 'data_transacao' in df.columns:
        df['data_transacao'] = pd.to_datetime(df['data_transacao'], unit='ms', errors='coerce', utc=True)

    for col in ['quantidade', 'valor_unitario', 'valor_total_emitter']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    logger.info(f"Loaded {len(df)} rows")
    return df


def write_fact_sales_batched(repo: PostgresRepository, df: pd.DataFrame, client_id: str):
    """Write fact_sales in batches with pauses to avoid quota issues."""

    logger.info("Loading dimension lookups...")

    # Load lookups
    def normalize_doc(val):
        return str(val) if val is not None else None

    customers = {}
    result = repo.db_session.execute(
        text("SELECT customer_id, cpf_cnpj FROM analytics_v2.dim_customer WHERE client_id = :cid"),
        {"cid": client_id}
    ).fetchall()
    for row in result:
        customers[normalize_doc(row.cpf_cnpj)] = row.customer_id
    logger.info(f"  Loaded {len(customers)} customers")

    suppliers = {}
    result = repo.db_session.execute(
        text("SELECT supplier_id, cnpj FROM analytics_v2.dim_supplier WHERE client_id = :cid"),
        {"cid": client_id}
    ).fetchall()
    for row in result:
        suppliers[normalize_doc(row.cnpj)] = row.supplier_id
    logger.info(f"  Loaded {len(suppliers)} suppliers")

    products = {}
    result = repo.db_session.execute(
        text("SELECT product_id, product_name FROM analytics_v2.dim_product WHERE client_id = :cid"),
        {"cid": client_id}
    ).fetchall()
    for row in result:
        products[row.product_name] = row.product_id
    logger.info(f"  Loaded {len(products)} products")

    # Clear existing fact_sales
    logger.info("Clearing existing fact_sales...")
    repo.db_session.execute(
        text("DELETE FROM analytics_v2.fact_sales WHERE client_id = :cid"),
        {"cid": client_id}
    )
    repo.db_session.commit()

    # Process in batches
    total_rows = len(df)
    total_inserted = 0
    total_skipped = 0

    for batch_start in range(0, total_rows, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_rows)
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(f"Processing batch {batch_num}/{total_batches} (rows {batch_start}-{batch_end})...")

        batch_df = df.iloc[batch_start:batch_end]
        values = []
        skipped = 0

        for _, row in batch_df.iterrows():
            receiver_cpf = normalize_doc(row.get('receiver_cpf_cnpj'))
            emitter_cnpj = normalize_doc(row.get('emitter_cnpj'))
            product_name = row.get('raw_product_description')

            customer_id = customers.get(receiver_cpf)
            supplier_id = suppliers.get(emitter_cnpj)
            product_id = products.get(product_name)

            if not customer_id or not supplier_id or not product_id:
                skipped += 1
                continue

            values.append((
                client_id,
                customer_id,
                supplier_id,
                product_id,
                row.get('order_id'),
                row.get('data_transacao'),
                float(row.get('quantidade', 0) or 0),
                float(row.get('valor_unitario', 0) or 0),
                float(row.get('valor_total_emitter', 0) or 0),
                receiver_cpf,
                emitter_cnpj
            ))

        if values:
            from psycopg2.extras import execute_values
            conn = repo.db_session.connection().connection
            cursor = conn.cursor()

            execute_values(
                cursor,
                """
                INSERT INTO analytics_v2.fact_sales (
                    client_id, customer_id, supplier_id, product_id,
                    order_id, data_transacao, quantidade, valor_unitario, valor_total,
                    customer_cpf_cnpj, supplier_cnpj,
                    created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                page_size=1000
            )
            conn.commit()
            total_inserted += len(values)

        total_skipped += skipped
        logger.info(f"  Inserted {len(values)}, skipped {skipped}")

        # Pause between batches to avoid quota
        if batch_end < total_rows:
            logger.info("  Pausing 2s to avoid quota...")
            time.sleep(2)

    logger.info(f"✅ Total inserted: {total_inserted}, skipped: {total_skipped}")
    return total_inserted


def main():
    repo = None
    try:
        logger.info("=" * 60)
        logger.info("ETL: Load fact_sales in batches")
        logger.info("=" * 60)

        df = load_csv()
        repo = PostgresRepository()

        inserted = write_fact_sales_batched(repo, df, TEST_CLIENT_ID)

        logger.info("=" * 60)
        logger.info(f"ETL completed! Inserted {inserted} fact_sales records")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        return 1
    finally:
        if repo:
            repo.close()


if __name__ == "__main__":
    sys.exit(main())
