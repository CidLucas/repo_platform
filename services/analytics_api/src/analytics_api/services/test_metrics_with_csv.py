#!/usr/bin/env python3
"""
Standalone test script to validate metrics aggregation using CSV data.

This script replicates the core MetricService aggregation logic to test
the data processing pipeline independently, without external dependencies.

Usage:
    cd services/analytics_api
    poetry run python src/analytics_api/services/test_metrics_with_csv.py
"""
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CSV file path (same directory as this script)
CSV_PATH = Path(__file__).parent / "product_invoices (1).csv"

# Column mapping from CSV to canonical schema
COLUMN_MAPPING = {
    # Order/Transaction fields
    "id_operatorinvoice": "order_id",
    "emittedat_operatorinvoice": "data_transacao",

    # Emitter (supplier) fields
    "emitterlegalname": "emitter_nome",
    "emitterlegaldoc": "emitter_cnpj",
    "emitterphone": "emitter_telefone",
    "emitterstateuf": "emitterstateuf",

    # Receiver (customer) fields
    "receiverlegalname": "receiver_nome",
    "receiverlegaldoc": "receiver_cpf_cnpj",
    "receiverphone": "receiver_telefone",
    "receiverstreet": "receiver_rua",
    "receivernumber": "receiver_numero",
    "receiverneighborhood": "receiver_bairro",
    "receivercity": "receiver_cidade",
    "receiverstateuf": "receiver_uf",
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
    logger.info(f"📂 Loading CSV from: {CSV_PATH}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    # Load CSV
    df = pd.read_csv(CSV_PATH, low_memory=False)
    logger.info(f"✓ Loaded {len(df)} rows, {len(df.columns)} columns")

    # Show original columns
    logger.info(f"📋 Original columns (first 20): {list(df.columns)[:20]}...")

    # Apply column mapping
    rename_map = {}
    for source_col, canonical_col in COLUMN_MAPPING.items():
        if source_col in df.columns:
            rename_map[source_col] = canonical_col
        else:
            logger.warning(f"⚠️  Source column '{source_col}' not found in CSV")

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

    # Show data quality
    logger.info("\n📈 Data Quality Summary:")
    for col in ['order_id', 'data_transacao', 'receiver_nome', 'emitter_nome', 'valor_total_emitter', 'quantidade']:
        if col in df.columns:
            null_pct = (df[col].isna().sum() / len(df)) * 100
            unique = df[col].nunique()
            logger.info(f"   {col}: {null_pct:.1f}% null, {unique:,} unique")

    return df


def aggregate_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate data by customer (receiver)."""
    logger.info("\n👥 Aggregating customers...")

    if 'receiver_nome' not in df.columns:
        logger.error("Missing receiver_nome column")
        return pd.DataFrame()

    # Group by customer
    agg = df.groupby('receiver_nome', dropna=False).agg(
        receita_total=('valor_total_emitter', 'sum'),
        quantidade_total=('quantidade', 'sum'),
        num_pedidos_unicos=('order_id', 'nunique'),
        primeira_venda=('data_transacao', 'min'),
        ultima_venda=('data_transacao', 'max'),
    ).reset_index()

    agg = agg.rename(columns={'receiver_nome': 'nome'})

    # Calculate derived metrics
    agg['ticket_medio'] = agg['receita_total'] / agg['num_pedidos_unicos'].replace(0, 1)
    agg['qtd_media_por_pedido'] = agg['quantidade_total'] / agg['num_pedidos_unicos'].replace(0, 1)

    # Recency
    today = pd.Timestamp.now(tz='UTC')
    agg['recencia_dias'] = (today - agg['ultima_venda']).dt.days

    # Sort by revenue
    agg = agg.sort_values('receita_total', ascending=False)

    logger.info(f"   ✓ Aggregated {len(agg)} customers")
    logger.info(f"   Total revenue: R$ {agg['receita_total'].sum():,.2f}")
    logger.info("   Top 5 customers by revenue:")
    for _, row in agg.head(5).iterrows():
        logger.info(f"      {row['nome'][:40]}: R$ {row['receita_total']:,.2f}")

    return agg


def aggregate_suppliers(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate data by supplier (emitter)."""
    logger.info("\n🏭 Aggregating suppliers...")

    if 'emitter_nome' not in df.columns:
        logger.error("Missing emitter_nome column")
        return pd.DataFrame()

    # Group by supplier
    agg = df.groupby('emitter_nome', dropna=False).agg(
        receita_total=('valor_total_emitter', 'sum'),
        quantidade_total=('quantidade', 'sum'),
        num_pedidos_unicos=('order_id', 'nunique'),
        primeira_venda=('data_transacao', 'min'),
        ultima_venda=('data_transacao', 'max'),
    ).reset_index()

    agg = agg.rename(columns={'emitter_nome': 'nome'})

    # Calculate derived metrics
    agg['ticket_medio'] = agg['receita_total'] / agg['num_pedidos_unicos'].replace(0, 1)

    # Sort by revenue
    agg = agg.sort_values('receita_total', ascending=False)

    logger.info(f"   ✓ Aggregated {len(agg)} suppliers")
    logger.info(f"   Total revenue: R$ {agg['receita_total'].sum():,.2f}")
    logger.info("   Top 5 suppliers by revenue:")
    for _, row in agg.head(5).iterrows():
        logger.info(f"      {row['nome'][:40]}: R$ {row['receita_total']:,.2f}")

    return agg


def aggregate_products(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate data by product."""
    logger.info("\n📦 Aggregating products...")

    if 'raw_product_description' not in df.columns:
        logger.error("Missing raw_product_description column")
        return pd.DataFrame()

    # Group by product
    agg = df.groupby('raw_product_description', dropna=False).agg(
        receita_total=('valor_total_emitter', 'sum'),
        quantidade_total=('quantidade', 'sum'),
        num_pedidos_unicos=('order_id', 'nunique'),
        primeira_venda=('data_transacao', 'min'),
        ultima_venda=('data_transacao', 'max'),
    ).reset_index()

    agg = agg.rename(columns={'raw_product_description': 'nome'})

    # Calculate derived metrics
    agg['valor_unitario_medio'] = agg['receita_total'] / agg['quantidade_total'].replace(0, 1)

    # Sort by revenue
    agg = agg.sort_values('receita_total', ascending=False)

    logger.info(f"   ✓ Aggregated {len(agg)} products")
    logger.info(f"   Total revenue: R$ {agg['receita_total'].sum():,.2f}")
    logger.info("   Top 5 products by revenue:")
    for _, row in agg.head(5).iterrows():
        logger.info(f"      {row['nome'][:40]}: R$ {row['receita_total']:,.2f}")

    return agg


def calculate_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly time series."""
    logger.info("\n📈 Calculating time series...")

    if 'data_transacao' not in df.columns:
        logger.error("Missing data_transacao column")
        return pd.DataFrame()

    # Group by month
    df['month'] = df['data_transacao'].dt.to_period('M')

    monthly = df.groupby('month').agg(
        total_orders=('order_id', 'nunique'),
        total_revenue=('valor_total_emitter', 'sum'),
        total_quantity=('quantidade', 'sum'),
    ).reset_index()

    monthly['month'] = monthly['month'].astype(str)

    logger.info(f"   ✓ Generated {len(monthly)} monthly data points")
    logger.info(f"   Date range: {monthly['month'].min()} to {monthly['month'].max()}")
    logger.info("\n   Last 6 months:")
    for _, row in monthly.tail(6).iterrows():
        logger.info(f"      {row['month']}: {row['total_orders']:,} orders, R$ {row['total_revenue']:,.2f}")

    return monthly


def calculate_home_metrics(df: pd.DataFrame, customers: pd.DataFrame, suppliers: pd.DataFrame, products: pd.DataFrame) -> dict:
    """Calculate home page scorecards."""
    logger.info("\n🏠 Calculating home metrics...")

    today = pd.Timestamp.now(tz='UTC')
    last_30_days = today - timedelta(days=30)

    # Filter last 30 days
    recent = df[df['data_transacao'] >= last_30_days]

    metrics = {
        "total_revenue": float(df['valor_total_emitter'].sum()),
        "total_orders": int(df['order_id'].nunique()),
        "total_customers": len(customers),
        "total_suppliers": len(suppliers),
        "total_products": len(products),
        "revenue_last_30_days": float(recent['valor_total_emitter'].sum()),
        "orders_last_30_days": int(recent['order_id'].nunique()),
        "avg_ticket": float(df['valor_total_emitter'].sum() / max(df['order_id'].nunique(), 1)),
    }

    logger.info(f"   Total Revenue: R$ {metrics['total_revenue']:,.2f}")
    logger.info(f"   Total Orders: {metrics['total_orders']:,}")
    logger.info(f"   Total Customers: {metrics['total_customers']:,}")
    logger.info(f"   Total Suppliers: {metrics['total_suppliers']:,}")
    logger.info(f"   Total Products: {metrics['total_products']:,}")
    logger.info(f"   Revenue (last 30 days): R$ {metrics['revenue_last_30_days']:,.2f}")
    logger.info(f"   Avg Ticket: R$ {metrics['avg_ticket']:,.2f}")

    return metrics


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("🧪 Standalone Metrics Aggregation Test")
    logger.info("=" * 80)

    try:
        # Step 1: Load and transform CSV
        df = load_and_transform_csv()

        # Step 2: Run aggregations
        customers = aggregate_customers(df)
        suppliers = aggregate_suppliers(df)
        products = aggregate_products(df)
        time_series = calculate_time_series(df)

        # Step 3: Calculate home metrics
        home_metrics = calculate_home_metrics(df, customers, suppliers, products)

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 AGGREGATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"   Raw data: {len(df):,} rows")
        logger.info(f"   Customers: {len(customers):,}")
        logger.info(f"   Suppliers: {len(suppliers):,}")
        logger.info(f"   Products: {len(products):,}")
        logger.info(f"   Time series points: {len(time_series):,}")
        logger.info(f"\n   Total Revenue: R$ {home_metrics['total_revenue']:,.2f}")
        logger.info(f"   Total Orders: {home_metrics['total_orders']:,}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Test completed successfully!")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
