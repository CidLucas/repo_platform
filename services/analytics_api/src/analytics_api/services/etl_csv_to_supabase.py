#!/usr/bin/env python3
"""
ETL Script to load CSV data and write to Supabase star schema.

This script:
1. Loads the product_invoices CSV file
2. Maps columns to the canonical schema
3. Writes to CSV files for export (workaround for Supabase schema issues)

Usage:
    cd services/analytics_api
    export SUPABASE_URL="https://xxx.supabase.co"
    export SUPABASE_KEY="..."
    poetry run python src/analytics_api/services/etl_csv_to_supabase.py

Schema: analytics_v2
- dim_customer: Customer dimension with aggregated metrics
- dim_supplier: Supplier dimension with aggregated metrics
- dim_product: Product dimension with aggregated metrics
- fact_sales: Transactional fact table (order_id, line_item_sequence)
"""
import datetime
import logging
import os
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
    """Repository that reads from CSV and writes to CSV files."""

    def __init__(self, csv_dataframe: pd.DataFrame):
        self._csv_df = csv_dataframe
        logger.info(f"CSVBackedRepository initialized with {len(csv_dataframe)} rows")

    def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
        logger.info(f"Returning CSV data for client {client_id} ({len(self._csv_df)} rows)")
        return self._csv_df.copy()

    def _get_column_mapping(self, client_id: str) -> dict[str, str] | None:
        return {col: col for col in self._csv_df.columns}

    @staticmethod
    def convert_value(val):
        """Convert a single value to a JSON-serializable type."""
        if val is pd.NaT or (isinstance(val, float) and np.isnan(val)):
            return None
        if isinstance(val, (pd.Timestamp, datetime.datetime)):
            return val.isoformat()
        if isinstance(val, np.datetime64):
            ts = pd.Timestamp(val)
            return ts.isoformat() if not pd.isnull(ts) else None
        if isinstance(val, (np.integer,)):
            return int(val)
        if isinstance(val, (np.floating,)):
            return float(val) if not np.isnan(val) else None
        return val

    @classmethod
    def convert_row(cls, row):
        """Convert a row (dict or Series) to JSON-serializable dict."""
        if hasattr(row, 'to_dict'):
            row = row.to_dict()
        elif not isinstance(row, dict):
            logger.warning(f"Row is not dict or Series: type={type(row)}, value={row}")
            try:
                row = dict(row)
            except Exception:
                logger.error(f"Cannot convert row to dict: {row}")
                return {}
        return {k: cls.convert_value(v) for k, v in row.items()}

    def write_star_customers(self, client_id, customers_data):
        """Write customer dimension data to CSV file."""
        logger.debug(f"customers_data type: {type(customers_data)}")

        if hasattr(customers_data, 'to_dict') and hasattr(customers_data, 'columns'):
            customers_data = customers_data.to_dict(orient='records')

        customers_data_serializable = [self.convert_row(row) for row in customers_data]
        logger.info(f"Writing {len(customers_data_serializable)} customers to CSV")

        export_path = Path.cwd() / "analytics_v2_dim_customer_export.csv"
        try:
            df_export = pd.DataFrame(customers_data_serializable)
            df_export.to_csv(export_path, index=False)
            logger.info(f"Wrote {len(df_export)} customers to CSV: {export_path}")
        except Exception as e:
            logger.error(f"Failed to write customers to CSV: {e}", exc_info=True)
            raise

    def write_star_suppliers(self, client_id, suppliers_data):
        """Write supplier dimension data to CSV file."""
        logger.debug(f"suppliers_data type: {type(suppliers_data)}")

        if hasattr(suppliers_data, 'to_dict') and hasattr(suppliers_data, 'columns'):
            suppliers_data = suppliers_data.to_dict(orient='records')

        suppliers_data_serializable = [self.convert_row(row) for row in suppliers_data]
        logger.info(f"Writing {len(suppliers_data_serializable)} suppliers to CSV")

        export_path = Path.cwd() / "analytics_v2_dim_supplier_export.csv"
        try:
            df_export = pd.DataFrame(suppliers_data_serializable)
            df_export.to_csv(export_path, index=False)
            logger.info(f"Wrote {len(df_export)} suppliers to CSV: {export_path}")
        except Exception as e:
            logger.error(f"Failed to write suppliers to CSV: {e}", exc_info=True)
            raise

    def write_star_products(self, client_id, products_data):
        """Write product dimension data to CSV file."""
        logger.debug(f"products_data type: {type(products_data)}")

        if hasattr(products_data, 'to_dict') and hasattr(products_data, 'columns'):
            products_data = products_data.to_dict(orient='records')

        products_data_serializable = [self.convert_row(row) for row in products_data]
        logger.info(f"Writing {len(products_data_serializable)} products to CSV")

        export_path = Path.cwd() / "analytics_v2_dim_product_export.csv"
        try:
            df_export = pd.DataFrame(products_data_serializable)
            df_export.to_csv(export_path, index=False)
            logger.info(f"Wrote {len(df_export)} products to CSV: {export_path}")
        except Exception as e:
            logger.error(f"Failed to write products to CSV: {e}", exc_info=True)
            raise

    def write_star_facts(self, client_id, facts_data):
        """Write fact table data to CSV file."""
        logger.debug(f"facts_data type: {type(facts_data)}")

        if hasattr(facts_data, 'to_dict') and hasattr(facts_data, 'columns'):
            facts_data = facts_data.to_dict(orient='records')

        facts_data_serializable = [self.convert_row(row) for row in facts_data]
        logger.info(f"Writing {len(facts_data_serializable)} facts to CSV")

        export_path = Path.cwd() / "analytics_v2_fact_sales_export.csv"
        try:
            df_export = pd.DataFrame(facts_data_serializable)
            df_export.to_csv(export_path, index=False)
            logger.info(f"Wrote {len(df_export)} facts to CSV: {export_path}")
        except Exception as e:
            logger.error(f"Failed to write facts to CSV: {e}", exc_info=True)
            raise

    def write_fact_sales(self, client_id, invoices_data) -> int:
        """Write fact_sales data to CSV file (override to avoid DB dependency)."""
        logger.debug(f"invoices_data type: {type(invoices_data)}")

        if hasattr(invoices_data, 'to_dict') and hasattr(invoices_data, 'columns'):
            invoices_data = invoices_data.to_dict(orient='records')

        invoices_data_serializable = [self.convert_row(row) for row in invoices_data]
        logger.info(f"Writing {len(invoices_data_serializable)} fact_sales to CSV")

        export_path = Path.cwd() / "analytics_v2_fact_sales_export.csv"
        try:
            df_export = pd.DataFrame(invoices_data_serializable)
            df_export.to_csv(export_path, index=False)
            logger.info(f"Wrote {len(df_export)} fact_sales to CSV: {export_path}")
            return len(df_export)
        except Exception as e:
            logger.error(f"Failed to write fact_sales to CSV: {e}", exc_info=True)
            raise


def main():
    """Main entry point for the ETL script."""
    try:
        df = load_and_transform_csv()

        repo = CSVBackedRepository(df)
        # MetricService.__init__ handles all aggregation and persistence
        metric_service = MetricService(repo, TEST_CLIENT_ID)

        # Print summary
        if hasattr(metric_service, 'df_clientes_agg') and not metric_service.df_clientes_agg.empty:
            total_revenue = metric_service.df_clientes_agg['receita_total'].sum()
            logger.info(f"Total Revenue: R$ {total_revenue:,.2f}")
        if hasattr(metric_service, 'df') and 'order_id' in metric_service.df.columns:
            logger.info(f"Total Orders: {metric_service.df['order_id'].nunique():,}")

        logger.info("ETL completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
