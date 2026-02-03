#!/usr/bin/env python3
"""
Standalone ETL Script to load CSV data and write to Supabase analytics_v2 star schema.

This script:
1. Loads the product_invoices CSV file
2. Maps columns to the canonical schema
3. Computes aggregations (customers, suppliers, products)
4. Writes directly to analytics_v2 tables via SQLAlchemy

Usage:
    cd services/analytics_api
    export DATABASE_URL="postgresql+psycopg2://..."
    poetry run python src/analytics_api/services/etl_csv_standalone.py
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CSV file path
CSV_PATH = Path(__file__).parent / "product_invoices (1).csv"

# Test client ID - use a fixed UUID for testing
TEST_CLIENT_ID = "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"

# Column mapping from CSV to canonical schema
COLUMN_MAPPING = {
    # Order/Transaction fields
    "id_operatorinvoice": "order_id",
    "emittedat_operatorinvoice": "data_transacao",

    # Emitter (supplier) fields
    "emitterlegalname": "emitter_nome",
    "emitterlegaldoc": "emitter_cnpj",
    "emitterphone": "emitter_telefone",
    "emitterstateuf": "emitter_uf",

    # Receiver (customer) fields
    "receiverlegalname": "receiver_nome",
    "receiverlegaldoc": "receiver_cpf_cnpj",
    "receiverphone": "receiver_telefone",
    "receiverstreet": "receiver_rua",
    "receivernumber": "receiver_numero",
    "receiverneighborhood": "receiver_bairro",
    "receivercity": "receiver_cidade",
    "receiverstateuf": "receiver_uf_customer",
    "receiverzipcode": "receiver_cep",

    # Product fields
    "description_product": "raw_product_description",
    "quantitytraded_product": "quantidade",
    "unitprice_product": "valor_unitario",
    "totalprice_product": "valor_total_emitter",

    # Status
    "status_operatorinvoice": "status",
}


def get_db_engine():
    """Create database engine from environment variable."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return create_engine(database_url, pool_pre_ping=True)


def load_and_transform_csv() -> pd.DataFrame:
    """Load CSV and transform to canonical schema."""
    logger.info(f"📂 Loading CSV from: {CSV_PATH}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    # Load CSV
    df = pd.read_csv(CSV_PATH, low_memory=False)
    logger.info(f"✓ Loaded {len(df)} rows, {len(df.columns)} columns")

    # Apply column mapping
    rename_map = {}
    for source_col, canonical_col in COLUMN_MAPPING.items():
        if source_col in df.columns:
            rename_map[source_col] = canonical_col

    df = df.rename(columns=rename_map)
    logger.info(f"🔄 Renamed {len(rename_map)} columns to canonical names")

    # Convert data_transacao from Unix timestamp (ms) to datetime
    if 'data_transacao' in df.columns:
        df['data_transacao'] = pd.to_datetime(df['data_transacao'], unit='ms', errors='coerce', utc=True)
        logger.info("📅 Converted data_transacao to datetime")
        logger.info(f"   Date range: {df['data_transacao'].min()} to {df['data_transacao'].max()}")

    # Ensure numeric columns are numeric
    numeric_cols = ['quantidade', 'valor_unitario', 'valor_total_emitter']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def write_dimension_customers(engine, client_id: str, df: pd.DataFrame) -> dict:
    """Write unique customers to dim_customer and return lookup dict."""
    logger.info("📝 Writing dim_customer...")

    # Get unique customers
    customer_cols = ['receiver_cpf_cnpj', 'receiver_nome', 'receiver_telefone',
                     'receiver_rua', 'receiver_numero', 'receiver_bairro',
                     'receiver_cidade', 'receiver_uf_customer', 'receiver_cep']
    available_cols = [c for c in customer_cols if c in df.columns]

    customers = df[available_cols].drop_duplicates(subset=['receiver_cpf_cnpj']).copy()
    customers = customers[customers['receiver_cpf_cnpj'].notna()]

    logger.info(f"   Found {len(customers)} unique customers")

    # Generate customer IDs and build lookup
    customer_lookup = {}

    # Use raw DBAPI connection and execute_values for bulk insert
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        # Delete dependent transactional rows first to avoid FK violations
        try:
            cursor.execute("DELETE FROM analytics_v2.fact_sales WHERE client_id = %s", (client_id,))
        except Exception:
            pass

        # Delete existing customers for this client
        cursor.execute("DELETE FROM analytics_v2.dim_customer WHERE client_id = %s", (client_id,))

        values = []
        for _, row in customers.iterrows():
            customer_id = str(uuid4())
            cpf_cnpj = row.get('receiver_cpf_cnpj')

            if not cpf_cnpj:
                continue

            customer_lookup[cpf_cnpj] = customer_id

            values.append((
                customer_id,
                client_id,
                cpf_cnpj,
                row.get('receiver_nome'),
                row.get('receiver_telefone'),
                row.get('receiver_rua'),
                row.get('receiver_numero'),
                row.get('receiver_bairro'),
                row.get('receiver_cidade'),
                row.get('receiver_uf_customer'),
                row.get('receiver_cep'),
            ))

        if values:
            insert_sql = (
                "INSERT INTO analytics_v2.dim_customer "
                "(customer_id, client_id, cpf_cnpj, name, telefone, "
                "endereco_rua, endereco_numero, endereco_bairro, endereco_cidade, endereco_uf, endereco_cep, created_at, updated_at) "
                "VALUES %s"
            )
            execute_values(
                cursor,
                insert_sql,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                page_size=1000,
            )

        raw_conn.commit()
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            raw_conn.close()
        except Exception:
            pass

    logger.info(f"   ✓ Written {len(customer_lookup)} customers")
    return customer_lookup


def write_dimension_suppliers(engine, client_id: str, df: pd.DataFrame) -> dict:
    """Write unique suppliers to dim_supplier and return lookup dict."""
    logger.info("📝 Writing dim_supplier...")

    # Get unique suppliers
    supplier_cols = ['emitter_cnpj', 'emitter_nome', 'emitter_telefone', 'emitter_uf']
    available_cols = [c for c in supplier_cols if c in df.columns]

    suppliers = df[available_cols].drop_duplicates(subset=['emitter_cnpj']).copy()
    suppliers = suppliers[suppliers['emitter_cnpj'].notna()]

    logger.info(f"   Found {len(suppliers)} unique suppliers")

    # Generate supplier IDs and build lookup
    supplier_lookup = {}

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.execute("DELETE FROM analytics_v2.dim_supplier WHERE client_id = %s", (client_id,))

        values = []
        for _, row in suppliers.iterrows():
            supplier_id = str(uuid4())
            cnpj = row.get('emitter_cnpj')

            if not cnpj:
                continue

            supplier_lookup[cnpj] = supplier_id
            values.append((supplier_id, client_id, cnpj, row.get('emitter_nome'), row.get('emitter_telefone'), row.get('emitter_uf')))

        if values:
            insert_sql = (
                "INSERT INTO analytics_v2.dim_supplier "
                "(supplier_id, client_id, cnpj, name, telefone, endereco_uf, created_at, updated_at) "
                "VALUES %s"
            )
            execute_values(cursor, insert_sql, values, template="(%s, %s, %s, %s, %s, %s, NOW(), NOW())", page_size=1000)

        raw_conn.commit()
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            raw_conn.close()
        except Exception:
            pass

    logger.info(f"   ✓ Written {len(supplier_lookup)} suppliers")
    return supplier_lookup


def write_dimension_products(engine, client_id: str, df: pd.DataFrame) -> dict:
    """Write unique products to dim_product and return lookup dict."""
    logger.info("📝 Writing dim_product...")

    # Get unique products
    products = df[['raw_product_description']].drop_duplicates().copy()
    products = products[products['raw_product_description'].notna()]

    logger.info(f"   Found {len(products)} unique products")

    # Generate product IDs and build lookup
    product_lookup = {}

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.execute("DELETE FROM analytics_v2.dim_product WHERE client_id = %s", (client_id,))

        values = []
        for _, row in products.iterrows():
            product_id = str(uuid4())
            product_name = row.get('raw_product_description')

            if not product_name:
                continue

            product_lookup[product_name] = product_id
            values.append((product_id, client_id, product_name))

        if values:
            insert_sql = (
                "INSERT INTO analytics_v2.dim_product (product_id, client_id, product_name, created_at, updated_at) VALUES %s"
            )
            execute_values(cursor, insert_sql, values, template="(%s, %s, %s, NOW(), NOW())", page_size=1000)

        raw_conn.commit()
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            raw_conn.close()
        except Exception:
            pass

    logger.info(f"   ✓ Written {len(product_lookup)} products")
    return product_lookup


def write_fact_sales(engine, client_id: str, df: pd.DataFrame,
                     customer_lookup: dict, supplier_lookup: dict, product_lookup: dict) -> int:
    """Write transaction-level fact_sales records."""
    logger.info("📝 Writing fact_sales...")

    with engine.connect() as conn:
        # Delete existing fact_sales for this client
        conn.execute(text("DELETE FROM analytics_v2.fact_sales WHERE client_id = :client_id"),
                     {"client_id": client_id})
        conn.commit()

    # Process in batches
    batch_size = 1000
    total_written = 0
    skipped = 0

    for start_idx in range(0, len(df), batch_size):
        batch = df.iloc[start_idx:start_idx + batch_size]
        values = []

        for _, row in batch.iterrows():
            cpf_cnpj = row.get('receiver_cpf_cnpj')
            cnpj = row.get('emitter_cnpj')
            product_name = row.get('raw_product_description')

            customer_id = customer_lookup.get(cpf_cnpj)
            supplier_id = supplier_lookup.get(cnpj)
            product_id = product_lookup.get(product_name)

            if not all([customer_id, supplier_id, product_id]):
                skipped += 1
                continue

            sale_id = str(uuid4())

            # Convert timestamp to datetime if needed
            sale_date = row.get('data_transacao')
            if pd.isna(sale_date):
                sale_date = None
            elif hasattr(sale_date, 'to_pydatetime'):
                sale_date = sale_date.to_pydatetime()

            values.append((
                client_id,
                customer_id,
                supplier_id,
                product_id,
                row.get('order_id'),
                sale_date,
                float(row.get('quantidade', 0) or 0),
                float(row.get('valor_unitario', 0) or 0),
                float(row.get('valor_total_emitter', 0) or 0),
                cpf_cnpj,
                cnpj,
            ))

        if values:
            raw_conn = engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                insert_sql = (
                    "INSERT INTO analytics_v2.fact_sales "
                    "(client_id, customer_id, supplier_id, product_id, order_id, data_transacao, quantidade, valor_unitario, valor_total, customer_cpf_cnpj, supplier_cnpj, created_at, updated_at) "
                    "VALUES %s"
                )
                execute_values(cursor, insert_sql, values,
                               template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                               page_size=500)
                raw_conn.commit()
                total_written += len(values)
                logger.info(f"   Batch {start_idx//batch_size + 1}: written {len(values)} rows...")
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
                try:
                    raw_conn.close()
                except Exception:
                    pass

    logger.info(f"   ✓ Written {total_written} fact_sales records ({skipped} skipped)")
    return total_written


def run_etl(client_id: str = TEST_CLIENT_ID):
    """Run the full ETL pipeline using CSV data."""
    logger.info("=" * 80)
    logger.info("🚀 ETL: CSV to Supabase Star Schema")
    logger.info("=" * 80)
    logger.info(f"   Client ID: {client_id}")

    # Step 1: Load and transform CSV
    df = load_and_transform_csv()

    # Show data quality
    logger.info("\n📈 Data Quality Summary:")
    for col in ['order_id', 'data_transacao', 'receiver_cpf_cnpj', 'emitter_cnpj',
                'raw_product_description', 'valor_total_emitter', 'quantidade']:
        if col in df.columns:
            null_pct = (df[col].isna().sum() / len(df)) * 100
            unique = df[col].nunique()
            logger.info(f"   {col}: {null_pct:.1f}% null, {unique:,} unique")

    # Step 2: Create database engine
    engine = get_db_engine()
    logger.info("\n✓ Connected to database")

    # Step 3: Write dimension tables
    logger.info("\n" + "=" * 80)
    logger.info("📊 Writing dimension tables...")
    logger.info("=" * 80)

    customer_lookup = write_dimension_customers(engine, client_id, df)
    supplier_lookup = write_dimension_suppliers(engine, client_id, df)
    product_lookup = write_dimension_products(engine, client_id, df)

    # Step 4: Write fact table
    logger.info("\n" + "=" * 80)
    logger.info("📊 Writing fact_sales...")
    logger.info("=" * 80)

    total_sales = write_fact_sales(engine, client_id, df, customer_lookup, supplier_lookup, product_lookup)

    return {
        "customers": len(customer_lookup),
        "suppliers": len(supplier_lookup),
        "products": len(product_lookup),
        "sales": total_sales,
    }


def main():
    """Main entry point."""
    try:
        # Check for client_id from command line or environment
        client_id = os.environ.get("CLIENT_ID", TEST_CLIENT_ID)
        if len(sys.argv) > 1:
            client_id = sys.argv[1]

        result = run_etl(client_id)

        logger.info("\n" + "=" * 80)
        logger.info("✅ ETL completed successfully!")
        logger.info("=" * 80)

        # Show summary
        logger.info("\n📊 Final Summary:")
        logger.info(f"   Customers: {result['customers']:,}")
        logger.info(f"   Suppliers: {result['suppliers']:,}")
        logger.info(f"   Products: {result['products']:,}")
        logger.info(f"   Sales: {result['sales']:,}")

        return 0

    except Exception as e:
        logger.error(f"\n❌ ETL failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
