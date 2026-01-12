# src/analytics_api/data_access/postgres_repository.py
import logging
import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from analytics_api.core.analytics_mapping import get_silver_table_name
from sqlalchemy import text
from sqlalchemy.orm import Session
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

class PostgresRepository:
    """
    Camada de acesso aos dados Prata (exclusivamente do nosso Postgres).
    (Corrigido para usar Session injetada)
    """
    # ALTERADO: Recebe a Session no construtor
    def __init__(self, db_session: Session):
        self.db_session = db_session # Armazena a sessão

    @staticmethod
    def _sanitize_numeric(value: Any, default: float = 0.0, max_value: float = 9999999999.99) -> float:
        """
        Sanitiza valores numéricos para evitar NaN/Inf e limitar valores extremos.
        Max value matches DECIMAL(12, 2) limit from database schema.
        """
        try:
            num = float(value)
            if pd.isna(num) or not np.isfinite(num):
                return default
            return min(max(num, 0), max_value)
        except (TypeError, ValueError):
            return default

    def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
        """
        Busca TODOS os dados da tabela Prata do cliente e carrega em
        um DataFrame Pandas para processamento em memória.

        IMPORTANT: Applies column_mapping from client_data_sources to translate
        source column names to canonical names.
        """
        table_name = get_silver_table_name(client_id)

        # Load column_mapping from client_data_sources
        column_mapping = self._get_column_mapping(client_id)

        # Build SELECT query with column aliases
        if column_mapping:
            # Build SELECT clause: "source_col" AS canonical_col
            select_clauses = []
            for source_col, canonical_col in column_mapping.items():
                # Quote source column to handle special characters
                select_clauses.append(f'"{source_col}" AS {canonical_col}')

            query = f"SELECT {', '.join(select_clauses)} FROM {table_name}"

            logger.info(f"🔍 Querying silver table: {table_name}")
            logger.info(f"  📝 Applying column mapping: {len(column_mapping)} columns")
            logger.info(f"  Sample mappings (first 5):")
            for source, canonical in list(column_mapping.items())[:5]:
                logger.info(f"    '{source}' → {canonical}")
        else:
            # Fallback to SELECT * if no mapping available
            query = f"SELECT * FROM {table_name}"
            logger.warning(f"⚠️  No column_mapping found for client {client_id}, using SELECT *")
            logger.warning(f"  This will return raw column names instead of canonical names!")

        try:
            df = pd.read_sql(query, self.db_session.bind)
            logger.info(f"✓ Loaded {len(df)} rows from silver layer")
            logger.info(f"📋 Column names ({len(df.columns)}): {list(df.columns[:20])}{'...' if len(df.columns) > 20 else ''}")

            # Log sample of first row for debugging
            if not df.empty:
                logger.debug(f"Sample first row keys: {list(df.iloc[0].to_dict().keys())[:10]}")

            # FALLBACK: Generate synthetic order_id if missing
            if 'order_id' not in df.columns and not df.empty:
                logger.warning("⚠️  order_id column missing, generating synthetic IDs")

                # Strategy: Create composite key from available columns
                # Priority: transaction date + amount + customer/supplier
                id_components = []

                if 'data_transacao' in df.columns:
                    id_components.append(df['data_transacao'].astype(str))
                if 'valor_total_emitter' in df.columns:
                    id_components.append(df['valor_total_emitter'].astype(str))
                if 'emitter_nome' in df.columns:
                    id_components.append(df['emitter_nome'].astype(str))
                if 'receiver_nome' in df.columns:
                    id_components.append(df['receiver_nome'].astype(str))

                if id_components:
                    # Combine components and hash
                    composite_key = id_components[0]
                    for component in id_components[1:]:
                        composite_key = composite_key + '_' + component

                    df['order_id'] = composite_key.apply(lambda x: str(abs(hash(x)) % 10**10))  # 10-digit hash
                    logger.info(f"  ✓ Generated {len(df['order_id'].unique())} unique synthetic order_ids")
                else:
                    # Last resort: use row index
                    df['order_id'] = df.index.astype(str)
                    logger.warning(f"  ⚠️  Using row index as order_id (not ideal for grouping)")

            # DATA QUALITY CHECK
            if not df.empty:
                logger.info(f"\n{'='*80}")
                logger.info(f"[DATA QUALITY CHECK]")
                logger.info(f"  Total rows: {len(df)}")

                # Check each column for NULL percentage
                quality_warnings = []
                for col in df.columns:
                    null_count = df[col].isna().sum()
                    null_pct = (null_count / len(df)) * 100
                    unique_vals = df[col].nunique()

                    if null_pct == 100:
                        quality_warnings.append(f"{col}: 100% NULL (completely empty!)")
                    elif null_pct > 50:
                        quality_warnings.append(f"{col}: {null_pct:.1f}% NULL (low quality)")
                    elif null_pct > 0:
                        logger.debug(f"  ℹ️  {col}: {null_pct:.1f}% NULL, {unique_vals:,} unique values")
                    else:
                        logger.debug(f"  ✓ {col}: 100% populated, {unique_vals:,} unique values")

                if quality_warnings:
                    logger.warning(f"  ⚠️  Quality Issues Detected:")
                    for warning in quality_warnings:
                        logger.warning(f"    - {warning}")
                else:
                    logger.info(f"  ✓ All columns have good quality (< 50% NULL)")

                logger.info(f"{'='*80}\n")

            return df
        except Exception as e:
            logger.error(f"❌ Failed to load silver data from '{table_name}': {e}")
            logger.error(f"  Query attempted: {query[:200]}...")
            raise

    def _get_column_mapping(self, client_id: str) -> dict[str, str] | None:
        """
        Loads the column_mapping from client_data_sources.

        Returns:
            dict mapping source column names to canonical names,
            or None if no mapping exists
        """
        try:
            result = self.db_session.execute(
                text("""
                    SELECT column_mapping
                    FROM client_data_sources
                    WHERE client_id = :client_id
                      AND storage_type = 'foreign_table'
                      AND sync_status = 'active'
                    ORDER BY last_synced_at DESC
                    LIMIT 1
                """),
                {"client_id": client_id}
            ).fetchone()

            if result and result[0]:
                column_mapping = result[0]
                logger.info(f"✓ Loaded column_mapping for client {client_id}: {len(column_mapping)} mappings")
                return column_mapping
            else:
                logger.warning(f"⚠️  No column_mapping found in client_data_sources for client_id: {client_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Error loading column_mapping for client {client_id}: {e}")
            return None

    def get_order_metrics_by_date_range(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, Any]:
        """
        Reads order metrics from Gold table (analytics_gold_orders).
        Returns:
            dict com total, revenue, avg_order_value, by_status
        """
        query = text("""
            SELECT
                total_orders as total,
                total_revenue as revenue,
                avg_order_value,
                period_type
            FROM analytics_gold_orders
            WHERE client_id = :client_id
              AND period_type = 'all_time'
            LIMIT 1
        """)
        try:
            result = self.db_session.execute(
                query,
                {"client_id": client_id}
            ).fetchone()

            if not result:
                return {"total": 0, "revenue": 0.0, "avg_order_value": 0.0, "by_status": {}}

            # Gold table only has all_time aggregates, by_status not stored
            return {
                "total": result.total or 0,
                "revenue": float(result.revenue or 0),
                "avg_order_value": float(result.avg_order_value or 0),
                "by_status": {}  # Not available in Gold, would need separate table
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de pedidos do Gold: {e}")
            self.db_session.rollback()
            return {"total": 0, "revenue": 0.0, "avg_order_value": 0.0, "by_status": {}}

    def get_product_metrics_by_date_range(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, Any]:
        """Reads product metrics from Gold table (analytics_gold_products)."""
        # Aggregate query
        query = text("""
            SELECT
                COALESCE(SUM(total_quantity_sold), 0) as total_sold,
                COUNT(DISTINCT product_name) as unique_products,
                COALESCE(AVG(avg_price), 0) as avg_price
            FROM analytics_gold_products
            WHERE client_id = :client_id
              AND period_type = 'all_time'
        """)
        # Top sellers
        top_sellers_query = text("""
            SELECT
                product_name as name,
                total_quantity_sold as quantity,
                total_revenue as revenue
            FROM analytics_gold_products
            WHERE client_id = :client_id
              AND period_type = 'all_time'
            ORDER BY total_revenue DESC
            LIMIT 10
        """)
        try:
            result = self.db_session.execute(
                query,
                {"client_id": client_id}
            ).fetchone()
            top_sellers = self.db_session.execute(
                top_sellers_query,
                {"client_id": client_id}
            ).fetchall()
            return {
                "total_sold": int(result.total_sold or 0) if result else 0,
                "unique_products": result.unique_products or 0 if result else 0,
                "avg_price": float(result.avg_price or 0) if result else 0.0,
                "top_sellers": [
                    {"name": r.name, "quantity": int(r.quantity), "revenue": float(r.revenue)}
                    for r in top_sellers
                ],
                "low_stock_alerts": 0  # Placeholder - requires inventory table
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de produtos do Gold: {e}")
            self.db_session.rollback()
            return {"total_sold": 0, "unique_products": 0, "avg_price": 0.0, "top_sellers": [], "low_stock_alerts": 0}

    def get_customer_metrics_by_date_range(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, Any]:
        """Reads customer metrics from Gold table (analytics_gold_customers)."""
        # Total active customers from Gold
        query = text("""
            SELECT
                COUNT(DISTINCT customer_name) as total_active,
                COUNT(DISTINCT CASE
                    WHEN first_order_date >= :start_date THEN customer_name
                END) as new_customers,
                COUNT(DISTINCT CASE
                    WHEN first_order_date < :start_date THEN customer_name
                END) as returning_customers,
                COALESCE(AVG(lifetime_value), 0) as avg_lifetime_value
            FROM analytics_gold_customers
            WHERE client_id = :client_id
              AND period_type = 'all_time'
        """)
        try:
            result = self.db_session.execute(
                query,
                {"client_id": client_id, "start_date": start_date}
            ).fetchone()

            if not result:
                return {"total_active": 0, "new_customers": 0, "returning_customers": 0, "avg_lifetime_value": 0.0}

            return {
                "total_active": result.total_active or 0,
                "new_customers": result.new_customers or 0,
                "returning_customers": result.returning_customers or 0,
                "avg_lifetime_value": float(result.avg_lifetime_value or 0)
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de clientes do Gold: {e}")
            self.db_session.rollback()
            return {"total_active": 0, "new_customers": 0, "returning_customers": 0, "avg_lifetime_value": 0.0}

    def get_or_create_cliente_vizu_id(self, external_user_id: str) -> str:
        """
        Busca ou cria um cliente_vizu_id associado ao external_user_id (Supabase user id).
        Retorna o cliente_vizu_id (UUID em string).
        """
        # Exemplo: tabela clientes (id UUID, external_user_id TEXT UNIQUE)
        result = self.db_session.execute(
            text("""
                SELECT id FROM clientes WHERE external_user_id = :external_user_id
            """),
            {"external_user_id": external_user_id}
        ).fetchone()
        if result:
            return str(result.id)
        # Cria novo cliente
        new_id = self.db_session.execute(
            text("""
                INSERT INTO clientes (external_user_id) VALUES (:external_user_id) RETURNING id
            """),
            {"external_user_id": external_user_id}
        ).fetchone().id
        self.db_session.commit()
        return str(new_id)

    def ensure_cliente_vizu_exists(
        self,
        external_user_id: str,
        email: str | None = None,
        client_id: str | None = None  # noqa: ARG002 - kept for API compatibility
    ) -> str:
        """
        Ensures a clientes_vizu record exists for the user.
        Creates one if it doesn't exist using external_user_id.

        Args:
            external_user_id: Supabase user ID (from JWT sub claim)
            email: User email (optional, used as company name fallback)
            client_id: Unused, kept for API compatibility

        Returns:
            The cliente_vizu.client_id (UUID) - Production uses client_id as PK
        """
        try:
            # Check if record exists using external_user_id
            result = self.db_session.execute(
                text("""
                    SELECT client_id FROM clientes_vizu WHERE external_user_id = :external_user_id
                """),
                {"external_user_id": external_user_id}
            ).fetchone()

            if result:
                # Return the existing client_id
                return str(result[0])

            # Create new record with external_user_id
            # Schema: client_id (UUID PK), external_user_id (TEXT UNIQUE), nome_empresa, tipo_cliente, tier
            new_result = self.db_session.execute(
                text("""
                    INSERT INTO clientes_vizu (
                        external_user_id,
                        nome_empresa,
                        tipo_cliente,
                        tier,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :external_user_id,
                        :nome_empresa,
                        'standard',
                        'free',
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (external_user_id) DO UPDATE
                    SET updated_at = NOW()
                    RETURNING client_id
                """),
                {
                    "external_user_id": external_user_id,
                    "nome_empresa": email or "Empresa"
                }
            ).fetchone()
            self.db_session.commit()
            created_client_id = str(new_result[0])
            logger.info(f"Created clientes_vizu record with client_id={created_client_id} for external_user_id={external_user_id}")
            return created_client_id

        except Exception as e:
            logger.error(f"Error ensuring clientes_vizu record: {e}", exc_info=True)
            self.db_session.rollback()
            # Return the external_user_id as fallback
            return external_user_id

    def _get_gold_table_single(self, table_name: str, client_id: str) -> dict:
        """
        Helper genérico para buscar uma única linha de uma tabela gold filtrada por client_id.
        """
        query = text(f"SELECT * FROM {table_name} WHERE client_id = :client_id")
        result = self.db_session.execute(query, {"client_id": client_id}).fetchone()
        return dict(result._mapping) if result else {}

    def _get_gold_table_multiple(self, table_name: str, client_id: str) -> list[dict]:
        """
        Helper genérico para buscar múltiplas linhas de uma tabela gold filtrada por client_id.
        """
        query = text(f"SELECT * FROM {table_name} WHERE client_id = :client_id")
        result = self.db_session.execute(query, {"client_id": client_id}).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def get_gold_orders_metrics(self, client_id: str) -> dict:
        """
        Busca métricas agregadas da view ouro de pedidos (analytics_gold_orders).
        Retorna um dicionário com os dados da view filtrados por client_id.
        """
        return self._get_gold_table_single("analytics_gold_orders", client_id)

    def get_gold_products_metrics(self, client_id: str) -> list[dict]:
        """
        Busca métricas agregadas da view ouro de produtos (analytics_gold_products).
        Retorna uma lista de dicionários, um por produto, filtrados por client_id.
        """
        return self._get_gold_table_multiple("analytics_gold_products", client_id)

    def get_gold_customers_metrics(self, client_id: str) -> list[dict]:
        """
        Busca métricas agregadas da view ouro de clientes (analytics_gold_customers).
        Retorna uma lista de dicionários, um por cliente, filtrados por client_id.
        """
        return self._get_gold_table_multiple("analytics_gold_customers", client_id)

    def get_gold_suppliers_metrics(self, client_id: str) -> list[dict]:
        """
        Busca métricas agregadas da view ouro de fornecedores (analytics_gold_suppliers).
        Retorna uma lista de dicionários, um por fornecedor, filtrados por client_id.
        """
        return self._get_gold_table_multiple("analytics_gold_suppliers", client_id)

    def write_gold_customers(self, client_id: str, customers_data: list[dict]) -> int:
        """Bulk persist aggregated customer metrics to analytics_gold_customers."""
        if not customers_data:
            return 0
        try:
            self.db_session.execute(
                text("DELETE FROM analytics_gold_customers WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    customer.get("nome"),
                    customer.get("receiver_cpf_cnpj"),
                    int(customer.get("num_pedidos_unicos", 0)),
                    self._sanitize_numeric(customer.get("receita_total", 0)),
                    self._sanitize_numeric(customer.get("ticket_medio", 0)),
                    customer.get("primeira_venda"),
                    customer.get("ultima_venda"),
                    customer.get("cluster_tier"),
                    "all_time",
                    None,
                    None,
                )
                for customer in customers_data
            ]

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_customers (
                    client_id, customer_name, customer_cpf_cnpj,
                    total_orders, lifetime_value, avg_order_value,
                    first_order_date, last_order_date, customer_type, period_type,
                    period_start, period_end, calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(customers_data)} customer records to analytics_gold_customers for {client_id}")
            return len(customers_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write customer data: {e}", exc_info=True)
            return 0

    def write_gold_suppliers(self, client_id: str, suppliers_data: list[dict]) -> int:
        """Bulk persist aggregated supplier metrics to analytics_gold_suppliers."""
        if not suppliers_data:
            return 0
        try:
            self.db_session.execute(
                text("DELETE FROM analytics_gold_suppliers WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    supplier.get("nome"),
                    supplier.get("emitter_cnpj"),
                    int(supplier.get("num_pedidos_unicos", 0)),
                    self._sanitize_numeric(supplier.get("receita_total", 0)),
                    self._sanitize_numeric(supplier.get("ticket_medio", 0)),
                    int(supplier.get("quantidade_total", 0)),
                    "all_time",
                    None,
                    None,
                )
                for supplier in suppliers_data
            ]

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_suppliers (
                    client_id, supplier_name, supplier_cnpj,
                    total_orders, total_revenue, avg_order_value, unique_products, period_type,
                    period_start, period_end, calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(suppliers_data)} supplier records to analytics_gold_suppliers for {client_id}")
            return len(suppliers_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write supplier data: {e}", exc_info=True)
            return 0

    def write_gold_products(self, client_id: str, products_data: list[dict]) -> int:
        """Bulk persist aggregated product metrics to analytics_gold_products with NaN/Inf clamping."""
        if not products_data:
            return 0
        try:
            self.db_session.execute(
                text("DELETE FROM analytics_gold_products WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    product.get("nome"),
                    self._sanitize_numeric(product.get("quantidade_total", 0)),
                    self._sanitize_numeric(product.get("receita_total", 0)),
                    self._sanitize_numeric(product.get("valor_unitario_medio", 0)),
                    int(product.get("num_pedidos_unicos", 0)),
                    "all_time",
                    None,
                    None,
                )
                for product in products_data
            ]

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_products (
                    client_id, product_name,
                    total_quantity_sold, total_revenue, avg_price, order_count, period_type,
                    period_start, period_end, calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(products_data)} product records to analytics_gold_products for {client_id}")
            return len(products_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write product data: {e}", exc_info=True)
            return 0

    def write_gold_orders(self, client_id: str, orders_metrics: dict) -> bool:
        """Persist aggregated order metrics to analytics_gold_orders."""
        if not orders_metrics:
            return False
        try:
            self.db_session.execute(
                text("DELETE FROM analytics_gold_orders WHERE client_id = :client_id AND period_type = :period_type"),
                {"client_id": client_id, "period_type": "all_time"}
            )

            self.db_session.execute(text(
                """
                INSERT INTO analytics_gold_orders (
                    client_id, total_orders, total_revenue, avg_order_value,
                    by_status, period_type, period_start, period_end, calculated_at, created_at, updated_at
                ) VALUES (
                    :client_id, :total_orders, :total_revenue, :avg_order_value,
                    CAST(:by_status AS jsonb), :period_type, :period_start, :period_end, NOW(), NOW(), NOW()
                )
                """
            ), {
                "client_id": client_id,
                "total_orders": int(orders_metrics.get("total_orders", 0)),
                "total_revenue": self._sanitize_numeric(orders_metrics.get("total_revenue", 0)),
                "avg_order_value": self._sanitize_numeric(orders_metrics.get("avg_order_value", 0)),
                "by_status": json.dumps({}),
                "period_type": "all_time",
                "period_start": None,  # NULL for all_time aggregation
                "period_end": None     # NULL for all_time aggregation
            })
            self.db_session.commit()
            logger.info(f"✓ Wrote order metrics to analytics_gold_orders: total_orders={orders_metrics.get('total_orders', 0)}, revenue={orders_metrics.get('total_revenue', 0):.2f}")
            return True
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to write order data: {e}", exc_info=True)
            return False

    # ---
    # Gold Chart Data Write Methods
    # ---

    def write_gold_time_series(self, client_id: str, chart_data: list[dict]) -> int:
        """Bulk persist time-series chart data to analytics_gold_time_series."""
        if not chart_data:
            return 0
        try:
            # Delete existing time series data for this client
            self.db_session.execute(
                text("DELETE FROM analytics_gold_time_series WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    point.get("chart_type"),
                    point.get("dimension"),
                    point.get("period"),
                    point.get("period_date"),
                    int(point.get("total", 0)),
                )
                for point in chart_data
            ]

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_time_series (
                    client_id, chart_type, dimension, period, period_date, total,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(chart_data)} time series points for {client_id}")
            return len(chart_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write time series data: {e}", exc_info=True)
            return 0

    def write_gold_regional(self, client_id: str, chart_data: list[dict]) -> int:
        """Bulk persist regional breakdown chart data to analytics_gold_regional."""
        if not chart_data:
            return 0
        try:
            # Delete existing regional data for this client and chart type
            chart_types = set(point.get("chart_type") for point in chart_data)
            for chart_type in chart_types:
                self.db_session.execute(
                    text("DELETE FROM analytics_gold_regional WHERE client_id = :client_id AND chart_type = :chart_type"),
                    {"client_id": client_id, "chart_type": chart_type}
                )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    point.get("chart_type"),
                    point.get("dimension"),
                    point.get("region_name"),
                    point.get("region_type"),
                    int(point.get("total", 0)),
                    int(point.get("contagem", 0)),
                    float(point.get("percentual", 0)),
                )
                for point in chart_data
            ]

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_regional (
                    client_id, chart_type, dimension, region_name, region_type,
                    total, contagem, percentual, calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(chart_data)} regional points for {client_id}")
            return len(chart_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write regional data: {e}", exc_info=True)
            return 0

    def write_gold_last_orders(self, client_id: str, orders_data: list[dict]) -> int:
        """Bulk persist last orders snapshot to analytics_gold_last_orders."""
        if not orders_data:
            return 0
        try:
            # Delete existing last orders for this client
            self.db_session.execute(
                text("DELETE FROM analytics_gold_last_orders WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    order.get("order_id"),
                    order.get("data_transacao"),
                    order.get("id_cliente"),
                    self._sanitize_numeric(order.get("ticket_pedido", 0)),
                    int(order.get("qtd_produtos", 0)),
                    int(order.get("order_rank", 0)),
                )
                for order in orders_data
            ]

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_last_orders (
                    client_id, order_id, data_transacao, id_cliente,
                    ticket_pedido, qtd_produtos, order_rank,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(orders_data)} last orders for {client_id}")
            return len(orders_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write last orders: {e}", exc_info=True)
            return 0

    # ---
    # Gold Chart Data Read Methods
    # ---

    def get_gold_time_series(self, client_id: str, chart_type: str) -> list[dict]:
        """Retrieve time-series chart data from analytics_gold_time_series."""
        try:
            result = self.db_session.execute(
                text("""
                    SELECT period AS name, total
                    FROM analytics_gold_time_series
                    WHERE client_id = :client_id AND chart_type = :chart_type
                    ORDER BY period_date ASC
                """),
                {"client_id": client_id, "chart_type": chart_type}
            ).fetchall()

            return [{"name": row.name, "total": int(row.total)} for row in result]
        except Exception as e:
            logger.error(f"❌ Failed to read time series {chart_type}: {e}", exc_info=True)
            return []

    def get_gold_regional(self, client_id: str, chart_type: str) -> list[dict]:
        """Retrieve regional breakdown chart data from analytics_gold_regional."""
        try:
            result = self.db_session.execute(
                text("""
                    SELECT region_name AS name, total, contagem, percentual
                    FROM analytics_gold_regional
                    WHERE client_id = :client_id AND chart_type = :chart_type
                    ORDER BY total DESC
                """),
                {"client_id": client_id, "chart_type": chart_type}
            ).fetchall()

            return [
                {
                    "name": row.name,
                    "total": int(row.total),
                    "contagem": int(row.contagem),
                    "percentual": float(row.percentual)
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"❌ Failed to read regional {chart_type}: {e}", exc_info=True)
            return []

    def get_gold_last_orders(self, client_id: str, limit: int = 20) -> list[dict]:
        """Retrieve last orders from analytics_gold_last_orders."""
        try:
            result = self.db_session.execute(
                text("""
                    SELECT order_id, data_transacao, id_cliente, ticket_pedido, qtd_produtos
                    FROM analytics_gold_last_orders
                    WHERE client_id = :client_id
                    ORDER BY order_rank ASC
                    LIMIT :limit
                """),
                {"client_id": client_id, "limit": limit}
            ).fetchall()

            return [
                {
                    "order_id": row.order_id,
                    "data_transacao": row.data_transacao,
                    "id_cliente": row.id_cliente,
                    "ticket_pedido": float(row.ticket_pedido),
                    "qtd_produtos": int(row.qtd_produtos)
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"❌ Failed to read last orders: {e}", exc_info=True)
            return []

