#!/usr/bin/env python3
"""
ETL Script to load CSV data and write DIRECTLY to Supabase analytics_v2 schema.

This script:
1. Loads the product_invoices CSV file
2. Maps columns to the canonical schema
3. Uses PostgresRepository with SQLAlchemy to write directly to analytics_v2 tables
   (bypasses PostgREST which doesn't support non-public schemas)

Usage:
    cd services/analytics_api
    export DATABASE_URL="postgresql://..."  # Direct Postgres connection
    poetry run python src/analytics_api/services/etl_csv_to_supabase_direct.py

Schema: analytics_v2
- dim_customer: Customer dimension with aggregated metrics
- dim_supplier: Supplier dimension with aggregated metrics
- dim_product: Product dimension with aggregated metrics
- fact_sales: Transactional fact table (order_id, line_item_sequence)
"""
import datetime
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.metric_service import MetricService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CSV file path
CSV_PATH = Path(__file__).parent / "product_invoices (1).csv"

# Test client ID
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


def load_and_transform_csv() -> pd.DataFrame:
    """Load CSV and transform to canonical schema."""
    logger.info(f"Loading CSV from: {CSV_PATH}")
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, low_memory=False)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    rename_map = {src: tgt for src, tgt in COLUMN_MAPPING.items() if src in df.columns}
    df = df.rename(columns=rename_map)
    logger.info(f"Renamed {len(rename_map)} columns to canonical names")

    if 'data_transacao' in df.columns:
        df['data_transacao'] = pd.to_datetime(df['data_transacao'], unit='ms', errors='coerce', utc=True)
        logger.info(f"Converted data_transacao to datetime")
        logger.info(f"Date range: {df['data_transacao'].min()} to {df['data_transacao'].max()}")

    numeric_cols = ['quantidade', 'valor_unitario', 'valor_total_emitter']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    logger.info(f"Data Quality Summary:")
    for col in ['order_id', 'data_transacao', 'receiver_nome', 'emitter_nome', 'valor_total_emitter', 'quantidade']:
        if col in df.columns:
            null_pct = (df[col].isna().sum() / len(df)) * 100
            unique = df[col].nunique()
            logger.info(f"  {col}: {null_pct:.1f}% null, {unique:,} unique")

    return df


class CSVBackedRepository(PostgresRepository):
    """
    Repository that reads from CSV but writes to real Supabase via SQLAlchemy.

    Inherits all write methods from PostgresRepository which use direct SQL
    to write to analytics_v2 schema (bypassing PostgREST limitations).
    """

    def __init__(self, csv_dataframe: pd.DataFrame):
        # Initialize parent with real DB connection
        super().__init__()
        self._csv_df = csv_dataframe
        logger.info(f"CSVBackedRepository initialized with {len(csv_dataframe)} rows (writing to real DB)")

    def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
        """Return CSV data instead of querying silver table."""
        logger.info(f"Returning CSV data for client {client_id} ({len(self._csv_df)} rows)")
        return self._csv_df.copy()

    def _get_column_mapping(self, client_id: str) -> dict[str, str] | None:
        """Return identity mapping since CSV already has canonical names."""
        return {col: col for col in self._csv_df.columns}


def main():
    """Main entry point for the ETL script."""
    repo = None
    try:
        logger.info("=" * 60)
        logger.info("ETL: CSV -> Supabase analytics_v2 (Direct SQL)")
        logger.info("=" * 60)

        df = load_and_transform_csv()

        # CSVBackedRepository reads from CSV but writes to real Supabase
        # Use context manager to ensure session is properly closed
        repo = CSVBackedRepository(df)

        logger.info(f"Target client_id: {TEST_CLIENT_ID}")
        logger.info("Writing to Supabase analytics_v2 schema via SQLAlchemy...")

        # MetricService.__init__ handles all aggregation and persistence
        metric_service = MetricService(repo, TEST_CLIENT_ID)

        # Print summary
        if hasattr(metric_service, 'df_clientes_agg') and not metric_service.df_clientes_agg.empty:
            total_revenue = metric_service.df_clientes_agg['receita_total'].sum()
            logger.info(f"Total Revenue: R$ {total_revenue:,.2f}")
        if hasattr(metric_service, 'df') and 'order_id' in metric_service.df.columns:
            logger.info(f"Total Orders: {metric_service.df['order_id'].nunique():,}")

        logger.info("=" * 60)
        logger.info("ETL completed successfully!")
        logger.info("Data written to Supabase analytics_v2 schema")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        return 1
    finally:
        # Always close repository session to release connection back to pool
        if repo is not None:
            repo.close()
            logger.info("Database session closed")


if __name__ == "__main__":
    sys.exit(main())
