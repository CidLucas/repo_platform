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
            self.db_session.rollback()  # Rollback to clear failed transaction state
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

    def _get_period_date_range(self, period: str) -> tuple[datetime, datetime] | None:
        """
        Converte string de período em date range.

        Args:
            period: 'week', 'month', 'quarter', 'year', 'all'

        Returns:
            Tuple (start_date, end_date) ou None se period='all'
        """
        if period == "all":
            return None

        from datetime import datetime, timedelta
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        ranges = {
            "week": (today_start - timedelta(days=7), now),
            "month": (today_start - timedelta(days=30), now),
            "quarter": (today_start - timedelta(days=90), now),
            "year": (today_start - timedelta(days=365), now),
        }
        return ranges.get(period, ranges["month"])

    def _get_gold_table_multiple(self, table_name: str, client_id: str) -> list[dict]:
        """
        Helper genérico para buscar múltiplas linhas de uma tabela gold filtrada por client_id.
        """
        query = text(f"SELECT * FROM {table_name} WHERE client_id = :client_id")
        result = self.db_session.execute(query, {"client_id": client_id}).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def get_gold_orders_metrics(self, client_id: str, period_type: str = "all_time") -> dict:
        """
        Busca métricas agregadas da view ouro de pedidos (analytics_gold_orders).
        Retorna um dicionário com os dados filtrados por client_id e period_type.

        Args:
            client_id: Client identifier
            period_type: "all_time" (default) or "monthly"

        Returns:
            Dict with order metrics for the specified period
        """
        query = text("""
            SELECT * FROM analytics_gold_orders
            WHERE client_id = :client_id AND period_type = :period_type
            LIMIT 1
        """)
        result = self.db_session.execute(query, {"client_id": client_id, "period_type": period_type}).fetchone()
        return dict(result._mapping) if result else {}

    def get_gold_orders_time_series(self, client_id: str) -> list[dict]:
        """
        Busca métricas de pedidos agrupadas por mês (time-series).
        Retorna uma lista de dicionários ordenada cronologicamente.

        Returns:
            List of dicts with monthly metrics, each containing:
            - period_start, period_end: Timestamps
            - total_orders, total_revenue, avg_order_value: Core metrics
            - quantidade_total, frequencia_pedidos_mes, recencia_dias: Enhanced metrics
            - primeira_transacao, ultima_transacao: Date boundaries
        """
        query = text("""
            SELECT *
            FROM analytics_gold_orders
            WHERE client_id = :client_id
              AND period_type = 'monthly'
            ORDER BY period_start ASC
        """)
        result = self.db_session.execute(query, {"client_id": client_id}).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def get_gold_products_metrics(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Busca métricas agregadas da view ouro de produtos (analytics_gold_products).
        Retorna uma lista de dicionários, um por produto, filtrados por client_id e período.

        Args:
            client_id: ID do cliente
            period: Período de filtro ('week', 'month', 'quarter', 'year', 'all')
        """
        date_range = self._get_period_date_range(period)
        if date_range is None:
            # period='all' - sem filtro de data
            return self._get_gold_table_multiple("analytics_gold_products", client_id)

        start_date, end_date = date_range
        query = text("""
            SELECT * FROM analytics_gold_products
            WHERE client_id = :client_id
              AND ultima_venda >= :start_date
              AND ultima_venda <= :end_date
        """)
        result = self.db_session.execute(query, {
            "client_id": client_id,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def get_gold_customers_metrics(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Busca métricas agregadas da view ouro de clientes (analytics_gold_customers).
        Retorna uma lista de dicionários, um por cliente, filtrados por client_id e período.

        Args:
            client_id: ID do cliente
            period: Período de filtro ('week', 'month', 'quarter', 'year', 'all')
        """
        date_range = self._get_period_date_range(period)
        if date_range is None:
            # period='all' - sem filtro de data
            return self._get_gold_table_multiple("analytics_gold_customers", client_id)

        start_date, end_date = date_range
        query = text("""
            SELECT * FROM analytics_gold_customers
            WHERE client_id = :client_id
              AND ultima_venda >= :start_date
              AND ultima_venda <= :end_date
        """)
        result = self.db_session.execute(query, {
            "client_id": client_id,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def get_products_by_customer_cpf_cnpj(self, client_id: str, customer_cpf_cnpj: str, limit: int = 10) -> list[dict]:
        """
        Get top products purchased by a specific customer using their CPF/CNPJ.

        Queries the silver layer (BigQuery FDW) to get product breakdown for this customer.

        Args:
            client_id: Client identifier
            customer_cpf_cnpj: Customer's CPF or CNPJ (unique government-issued ID)
            limit: Maximum number of products to return (default 10)

        Returns:
            List of dicts with product name, total quantity, total revenue, sorted by revenue desc
        """
        table_name = get_silver_table_name(client_id)
        column_mapping = self._get_column_mapping(client_id)

        if not column_mapping:
            logger.warning(f"No column mapping for client {client_id}, cannot get products by customer")
            return []

        # Find the source column names for required fields
        receiver_cpf_col = None
        product_col = None
        quantidade_col = None
        valor_col = None

        for source_col, canonical_col in column_mapping.items():
            if canonical_col == 'receiver_cpf_cnpj':
                receiver_cpf_col = source_col
            elif canonical_col == 'raw_product_description':
                product_col = source_col
            elif canonical_col == 'quantidade':
                quantidade_col = source_col
            elif canonical_col == 'valor_total_emitter':
                valor_col = source_col

        if not all([receiver_cpf_col, product_col]):
            logger.warning(f"Missing required columns for product lookup: receiver_cpf={receiver_cpf_col}, product={product_col}")
            return []

        try:
            # Build query to aggregate products by customer
            query = text(f"""
                SELECT
                    "{product_col}" as nome,
                    COALESCE(SUM(CAST("{quantidade_col}" AS NUMERIC)), 0) as quantidade_total,
                    COALESCE(SUM(CAST("{valor_col}" AS NUMERIC)), 0) as receita_total
                FROM {table_name}
                WHERE "{receiver_cpf_col}" = :customer_cpf_cnpj
                GROUP BY "{product_col}"
                ORDER BY receita_total DESC
                LIMIT :limit
            """)

            result = self.db_session.execute(query, {
                "customer_cpf_cnpj": customer_cpf_cnpj,
                "limit": limit
            }).fetchall()

            products = [dict(row._mapping) for row in result] if result else []
            logger.info(f"Found {len(products)} products for customer {customer_cpf_cnpj[:8]}...")
            return products

        except Exception as e:
            logger.error(f"Failed to get products for customer {customer_cpf_cnpj}: {e}")
            return []

    def get_gold_suppliers_metrics(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Busca métricas agregadas da view ouro de fornecedores (analytics_gold_suppliers).
        Retorna uma lista de dicionários, um por fornecedor, filtrados por client_id e período.

        Args:
            client_id: ID do cliente
            period: Período de filtro ('week', 'month', 'quarter', 'year', 'all')
        """
        date_range = self._get_period_date_range(period)
        if date_range is None:
            # period='all' - sem filtro de data
            return self._get_gold_table_multiple("analytics_gold_suppliers", client_id)

        start_date, end_date = date_range
        query = text("""
            SELECT * FROM analytics_gold_suppliers
            WHERE client_id = :client_id
              AND ultima_venda >= :start_date
              AND ultima_venda <= :end_date
        """)
        result = self.db_session.execute(query, {
            "client_id": client_id,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def write_gold_customers(self, client_id: str, customers_data: list[dict]) -> int:
        """Bulk persist aggregated customer metrics to analytics_gold_customers."""
        if not customers_data:
            return 0
        try:
            self.db_session.execute(
                text("DELETE FROM analytics_gold_customers WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data - include ALL ranking fields + contact info
            values = [
                (
                    client_id,
                    customer.get("nome"),
                    customer.get("receiver_cpf_cnpj"),
                    # Old columns (kept for backwards compatibility)
                    int(customer.get("num_pedidos_unicos", 0)),  # total_orders
                    self._sanitize_numeric(customer.get("receita_total", 0)),  # lifetime_value
                    self._sanitize_numeric(customer.get("ticket_medio", 0)),  # avg_order_value
                    customer.get("primeira_venda"),  # first_order_date
                    customer.get("ultima_venda"),  # last_order_date
                    customer.get("cluster_tier"),  # customer_type
                    "all_time",  # period_type
                    customer.get("period_start"),
                    customer.get("period_end"),
                    # New ranking columns (from 20260109 migration)
                    self._sanitize_numeric(customer.get("quantidade_total", 0)),
                    int(customer.get("num_pedidos_unicos", 0)),
                    self._sanitize_numeric(customer.get("ticket_medio", 0)),
                    self._sanitize_numeric(customer.get("qtd_media_por_pedido", 0)),
                    self._sanitize_numeric(customer.get("frequencia_pedidos_mes", 0)),
                    int(customer.get("recencia_dias", 0)),
                    self._sanitize_numeric(customer.get("valor_unitario_medio", 0)),
                    self._sanitize_numeric(customer.get("cluster_score", 0)),
                    customer.get("cluster_tier"),
                    customer.get("primeira_venda"),
                    customer.get("ultima_venda"),
                    # Contact and address fields (from 20260122 migration)
                    customer.get("receiver_telefone"),
                    customer.get("receiver_rua"),
                    customer.get("receiver_numero"),
                    customer.get("receiver_bairro"),
                    customer.get("receiver_cidade"),
                    customer.get("receiverstateuf") or customer.get("receiver_uf"),  # handle both naming conventions
                    customer.get("receiver_cep"),
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
                    period_start, period_end,
                    quantidade_total, num_pedidos_unicos, ticket_medio, qtd_media_por_pedido,
                    frequencia_pedidos_mes, recencia_dias, valor_unitario_medio,
                    cluster_score, cluster_tier, primeira_venda, ultima_venda,
                    telefone, endereco_rua, endereco_numero, endereco_bairro,
                    endereco_cidade, endereco_uf, endereco_cep,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
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

            # Prepare bulk data - include ALL ranking fields
            values = [
                (
                    client_id,
                    supplier.get("nome"),
                    supplier.get("emitter_cnpj"),
                    # Old columns (kept for backwards compatibility)
                    int(supplier.get("num_pedidos_unicos", 0)),  # total_orders
                    self._sanitize_numeric(supplier.get("receita_total", 0)),  # total_revenue
                    self._sanitize_numeric(supplier.get("ticket_medio", 0)),  # avg_order_value
                    0,  # unique_products (not calculated yet)
                    "all_time",  # period_type
                    supplier.get("period_start"),
                    supplier.get("period_end"),
                    # New ranking columns (from 20260109 migration)
                    self._sanitize_numeric(supplier.get("quantidade_total", 0)),
                    int(supplier.get("num_pedidos_unicos", 0)),
                    self._sanitize_numeric(supplier.get("ticket_medio", 0)),
                    self._sanitize_numeric(supplier.get("qtd_media_por_pedido", 0)),
                    self._sanitize_numeric(supplier.get("frequencia_pedidos_mes", 0)),
                    int(supplier.get("recencia_dias", 0)),
                    self._sanitize_numeric(supplier.get("valor_unitario_medio", 0)),
                    self._sanitize_numeric(supplier.get("cluster_score", 0)),
                    supplier.get("cluster_tier"),
                    supplier.get("primeira_venda"),
                    supplier.get("ultima_venda"),
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
                    period_start, period_end,
                    quantidade_total, num_pedidos_unicos, ticket_medio, qtd_media_por_pedido,
                    frequencia_pedidos_mes, recencia_dias, valor_unitario_medio,
                    cluster_score, cluster_tier, primeira_venda, ultima_venda,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
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

            # Prepare bulk data - include ALL ranking fields
            values = [
                (
                    client_id,
                    product.get("nome"),
                    # Old columns (kept for backwards compatibility)
                    self._sanitize_numeric(product.get("quantidade_total", 0)),  # total_quantity_sold
                    self._sanitize_numeric(product.get("receita_total", 0)),  # total_revenue
                    self._sanitize_numeric(product.get("valor_unitario_medio", 0)),  # avg_price
                    int(product.get("num_pedidos_unicos", 0)),  # order_count
                    "all_time",  # period_type
                    product.get("period_start"),
                    product.get("period_end"),
                    # New ranking columns (from 20260109 migration)
                    self._sanitize_numeric(product.get("quantidade_total", 0)),
                    int(product.get("num_pedidos_unicos", 0)),
                    self._sanitize_numeric(product.get("ticket_medio", 0)),
                    self._sanitize_numeric(product.get("qtd_media_por_pedido", 0)),
                    self._sanitize_numeric(product.get("frequencia_pedidos_mes", 0)),
                    int(product.get("recencia_dias", 0)),
                    self._sanitize_numeric(product.get("cluster_score", 0)),
                    product.get("cluster_tier"),
                    product.get("primeira_venda"),
                    product.get("ultima_venda"),
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
                    period_start, period_end,
                    quantidade_total, num_pedidos_unicos, ticket_medio, qtd_media_por_pedido,
                    frequencia_pedidos_mes, recencia_dias,
                    cluster_score, cluster_tier, primeira_venda, ultima_venda,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(products_data)} product records to analytics_gold_products for {client_id}")
            return len(products_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write product data: {e}", exc_info=True)
            return 0

    def write_gold_customer_products(self, client_id: str, customer_products_data: list[dict]) -> int:
        """
        Bulk persist customer-product relationships to analytics_gold_customer_products.
        This enables fast lookup of products per customer for ClienteDetailsModal.
        """
        if not customer_products_data:
            return 0
        try:
            # Delete existing records for this client
            self.db_session.execute(
                text("DELETE FROM analytics_gold_customer_products WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = [
                (
                    client_id,
                    cp.get("customer_cpf_cnpj"),
                    cp.get("customer_name"),
                    cp.get("product_name"),
                    self._sanitize_numeric(cp.get("receita_total", 0)),
                    self._sanitize_numeric(cp.get("quantidade_total", 0)),
                    int(cp.get("num_pedidos", 0)),
                    self._sanitize_numeric(cp.get("valor_unitario_medio", 0)),
                    cp.get("primeira_compra"),
                    cp.get("ultima_compra"),
                    "all_time",  # period_type
                )
                for cp in customer_products_data
            ]

            # Bulk INSERT using execute_values for performance
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_customer_products (
                    client_id, customer_cpf_cnpj, customer_name, product_name,
                    receita_total, quantidade_total, num_pedidos, valor_unitario_medio,
                    primeira_compra, ultima_compra, period_type,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(customer_products_data)} customer-product records for {client_id}")
            return len(customer_products_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write customer-product data: {e}", exc_info=True)
            return 0

    def get_gold_customer_products(self, client_id: str, customer_cpf_cnpj: str, limit: int = 10) -> list[dict]:
        """
        Get top products for a specific customer from the gold table.
        Returns products sorted by revenue (highest first).

        Args:
            client_id: Client identifier
            customer_cpf_cnpj: Customer's CPF or CNPJ
            limit: Maximum number of products to return (default 10)

        Returns:
            List of dicts with product_name, receita_total, quantidade_total, etc.
        """
        try:
            result = self.db_session.execute(
                text("""
                    SELECT
                        product_name as nome,
                        receita_total,
                        quantidade_total,
                        num_pedidos,
                        valor_unitario_medio,
                        primeira_compra,
                        ultima_compra
                    FROM analytics_gold_customer_products
                    WHERE client_id = :client_id
                      AND customer_cpf_cnpj = :customer_cpf_cnpj
                    ORDER BY receita_total DESC
                    LIMIT :limit
                """),
                {"client_id": client_id, "customer_cpf_cnpj": customer_cpf_cnpj, "limit": limit}
            ).fetchall()

            products = [dict(row._mapping) for row in result] if result else []
            logger.info(f"Found {len(products)} products from gold table for customer {customer_cpf_cnpj[:8]}...")
            return products
        except Exception as e:
            logger.error(f"Failed to get gold customer products: {e}")
            return []

    def get_customer_monthly_orders(self, client_id: str, customer_cpf_cnpj: str) -> list[dict]:
        """
        Get monthly order count for a specific customer from gold tables.
        Returns time series data showing num_pedidos per month.

        Args:
            client_id: Client identifier
            customer_cpf_cnpj: Customer's CPF or CNPJ

        Returns:
            List of dicts with month (YYYY-MM format) and num_pedidos
        """
        try:
            # Query analytics_gold_last_orders table which has transaction data
            result = self.db_session.execute(
                text("""
                    SELECT
                        TO_CHAR(DATE_TRUNC('month', data_transacao), 'YYYY-MM') as month,
                        COUNT(DISTINCT order_id) as num_pedidos
                    FROM analytics_gold_last_orders
                    WHERE client_id = :client_id
                      AND customer_cpf_cnpj = :customer_cpf_cnpj
                    GROUP BY DATE_TRUNC('month', data_transacao)
                    ORDER BY month ASC
                """),
                {"client_id": client_id, "customer_cpf_cnpj": customer_cpf_cnpj}
            ).fetchall()

            monthly_data = [dict(row._mapping) for row in result] if result else []
            logger.info(f"Found {len(monthly_data)} months of order data for customer {customer_cpf_cnpj[:8]}...")
            return monthly_data
        except Exception as e:
            logger.error(f"Failed to get customer monthly orders: {e}")
            return []

    def get_customers_by_product(self, client_id: str, product_name: str, limit: int = 100) -> list[dict]:
        """
        Get all customers who bought a specific product, with their spending metrics.
        Used for product-filtered customer list view.

        Returns customers sorted by revenue spent on this product (highest first),
        with percentage of their total spending.
        """
        try:
            result = self.db_session.execute(
                text("""
                    WITH customer_product AS (
                        SELECT
                            cp.customer_cpf_cnpj,
                            cp.customer_name,
                            cp.receita_total as produto_receita,
                            cp.quantidade_total as produto_quantidade,
                            cp.num_pedidos as produto_pedidos
                        FROM analytics_gold_customer_products cp
                        WHERE cp.client_id = :client_id
                          AND cp.product_name = :product_name
                    ),
                    customer_totals AS (
                        SELECT
                            customer_cpf_cnpj,
                            SUM(receita_total) as total_gasto
                        FROM analytics_gold_customer_products
                        WHERE client_id = :client_id
                        GROUP BY customer_cpf_cnpj
                    )
                    SELECT
                        cp.customer_cpf_cnpj,
                        cp.customer_name as nome,
                        cp.produto_receita,
                        cp.produto_quantidade,
                        cp.produto_pedidos,
                        ct.total_gasto as cliente_receita_total,
                        CASE WHEN ct.total_gasto > 0
                             THEN ROUND((cp.produto_receita / ct.total_gasto) * 100, 2)
                             ELSE 0
                        END as percentual_do_total
                    FROM customer_product cp
                    JOIN customer_totals ct ON cp.customer_cpf_cnpj = ct.customer_cpf_cnpj
                    ORDER BY cp.produto_receita DESC
                    LIMIT :limit
                """),
                {"client_id": client_id, "product_name": product_name, "limit": limit}
            ).fetchall()

            customers = [dict(row._mapping) for row in result] if result else []
            logger.info(f"Found {len(customers)} customers for product '{product_name[:30]}...'")
            return customers
        except Exception as e:
            logger.error(f"Failed to get customers by product: {e}")
            return []

    def get_distinct_products(self, client_id: str) -> list[dict]:
        """
        Get list of distinct products for dropdown filter.
        Returns product names with their total revenue for sorting.
        """
        try:
            result = self.db_session.execute(
                text("""
                    SELECT
                        product_name as nome,
                        SUM(receita_total) as receita_total,
                        COUNT(DISTINCT customer_cpf_cnpj) as total_clientes
                    FROM analytics_gold_customer_products
                    WHERE client_id = :client_id
                    GROUP BY product_name
                    ORDER BY receita_total DESC
                """),
                {"client_id": client_id}
            ).fetchall()

            products = [dict(row._mapping) for row in result] if result else []
            logger.info(f"Found {len(products)} distinct products for client {client_id}")
            return products
        except Exception as e:
            logger.error(f"Failed to get distinct products: {e}")
            return []

    def get_distinct_customers(self, client_id: str) -> list[dict]:
        """
        Get list of distinct customers for dropdown filter.
        Returns customer names with their total spending for sorting.
        """
        try:
            result = self.db_session.execute(
                text("""
                    SELECT
                        customer_cpf_cnpj,
                        customer_name as nome,
                        SUM(receita_total) as receita_total,
                        COUNT(DISTINCT product_name) as total_produtos
                    FROM analytics_gold_customer_products
                    WHERE client_id = :client_id
                    GROUP BY customer_cpf_cnpj, customer_name
                    ORDER BY receita_total DESC
                """),
                {"client_id": client_id}
            ).fetchall()

            customers = [dict(row._mapping) for row in result] if result else []
            logger.info(f"Found {len(customers)} distinct customers for client {client_id}")
            return customers
        except Exception as e:
            logger.error(f"Failed to get distinct customers: {e}")
            return []

    def write_gold_orders_bulk(self, client_id: str, orders_metrics_list: list[dict]) -> int:
        """
        Persist aggregated order metrics to analytics_gold_orders (bulk version).
        Handles both all-time and monthly period records.

        Args:
            client_id: Client identifier
            orders_metrics_list: List of metric dicts with period_type, metrics, and enhanced fields

        Returns:
            Number of records written
        """
        if not orders_metrics_list:
            logger.warning("No order metrics to write (empty list)")
            return 0

        try:
            # Delete ALL existing records for this client (all periods)
            self.db_session.execute(
                text("DELETE FROM analytics_gold_orders WHERE client_id = :client_id"),
                {"client_id": client_id}
            )

            # Prepare bulk data
            values = []
            for orders_metrics in orders_metrics_list:
                values.append((
                    client_id,
                    int(orders_metrics.get("total_orders", 0)),
                    self._sanitize_numeric(orders_metrics.get("total_revenue", 0)),
                    self._sanitize_numeric(orders_metrics.get("avg_order_value", 0)),
                    json.dumps({}),  # by_status - empty for now
                    orders_metrics.get("period_type", "all_time"),
                    orders_metrics.get("period_start"),
                    orders_metrics.get("period_end"),
                    # Enhanced metrics
                    self._sanitize_numeric(orders_metrics.get("quantidade_total", 0)),
                    self._sanitize_numeric(orders_metrics.get("frequencia_pedidos_mes", 0)),
                    int(orders_metrics.get("recencia_dias", 0)),
                    orders_metrics.get("primeira_transacao"),
                    orders_metrics.get("ultima_transacao"),
                ))

            # Bulk INSERT using psycopg2.extras.execute_values
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_gold_orders (
                    client_id, total_orders, total_revenue, avg_order_value,
                    by_status, period_type, period_start, period_end,
                    quantidade_total, frequencia_pedidos_mes, recencia_dias,
                    primeira_transacao, ultima_transacao,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="""(
                    %s, %s, %s, %s,
                    CAST(%s AS jsonb), %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    NOW(), NOW(), NOW()
                )""",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(orders_metrics_list)} order metric records")

            # Log breakdown
            period_counts = {}
            for metric in orders_metrics_list:
                period_type = metric.get("period_type", "unknown")
                period_counts[period_type] = period_counts.get(period_type, 0) + 1
            logger.info(f"  Period breakdown: {period_counts}")

            return len(orders_metrics_list)

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write order data: {e}", exc_info=True)
            return 0

    def write_gold_orders(self, client_id: str, orders_metrics: dict) -> bool:
        """
        Legacy method: Persist single order metrics record.
        Use write_gold_orders_bulk() for multi-period writes.
        """
        return self.write_gold_orders_bulk(client_id, [orders_metrics]) > 0

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
                    order.get("customer_cpf_cnpj") or order.get("id_cliente"),  # Support both names
                    order.get("customer_name"),
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
                    client_id, order_id, data_transacao, customer_cpf_cnpj,
                    customer_name, ticket_pedido, qtd_produtos, order_rank,
                    calculated_at, created_at, updated_at
                ) VALUES %s
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
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
            self.db_session.rollback()  # Rollback to clear failed transaction state
            return []

    def get_comparison_metrics_from_time_series(self, client_id: str, chart_type: str) -> dict:
        """
        Calculate comparison metrics (vs 7, 30, 90 days) from gold_time_series in a SINGLE query.

        This is much more efficient than making 4 separate queries for today/week/month/quarter.
        Uses monthly aggregated data from the time series table.

        Args:
            client_id: Client identifier
            chart_type: One of 'clientes_no_tempo', 'produtos_no_tempo', 'pedidos_no_tempo', 'fornecedores_no_tempo'

        Returns:
            Dict with keys: current_month, prev_month_avg, prev_3_months_avg, prev_12_months_avg,
                           vs_prev_month, vs_3_months, vs_12_months, trend
        """
        try:
            result = self.db_session.execute(
                text("""
                    WITH recent_data AS (
                        SELECT
                            period_date,
                            total,
                            ROW_NUMBER() OVER (ORDER BY period_date DESC) as rn
                        FROM analytics_gold_time_series
                        WHERE client_id = :client_id
                          AND chart_type = :chart_type
                        ORDER BY period_date DESC
                        LIMIT 12
                    )
                    SELECT
                        -- Current month (most recent)
                        MAX(CASE WHEN rn = 1 THEN total END) as current_month,
                        -- Previous month
                        MAX(CASE WHEN rn = 2 THEN total END) as prev_month,
                        -- Average of last 3 months (excluding current)
                        AVG(CASE WHEN rn BETWEEN 2 AND 4 THEN total END) as avg_3_months,
                        -- Average of last 12 months (excluding current)
                        AVG(CASE WHEN rn BETWEEN 2 AND 12 THEN total END) as avg_12_months
                    FROM recent_data
                """),
                {"client_id": client_id, "chart_type": chart_type}
            ).fetchone()

            if not result or result.current_month is None:
                return {
                    "current_month": 0,
                    "vs_prev_month": None,
                    "vs_3_months": None,
                    "vs_12_months": None,
                    "trend": "stable"
                }

            current = float(result.current_month or 0)
            prev_month = float(result.prev_month or 0)
            avg_3 = float(result.avg_3_months or 0)
            avg_12 = float(result.avg_12_months or 0)

            # Calculate percentage changes
            def calc_pct(current_val, prev_val):
                if prev_val == 0:
                    return 100.0 if current_val > 0 else None
                return round(((current_val - prev_val) / prev_val) * 100, 2)

            vs_prev = calc_pct(current, prev_month)
            vs_3 = calc_pct(current, avg_3)
            vs_12 = calc_pct(current, avg_12)

            # Determine trend
            values = [v for v in [vs_prev, vs_3, vs_12] if v is not None]
            if values:
                avg_change = sum(values) / len(values)
                trend = "up" if avg_change > 5 else ("down" if avg_change < -5 else "stable")
            else:
                trend = "stable"

            return {
                "current_month": int(current),
                "vs_prev_month": vs_prev,
                "vs_3_months": vs_3,
                "vs_12_months": vs_12,
                "trend": trend
            }

        except Exception as e:
            logger.error(f"❌ Failed to calculate comparison metrics for {chart_type}: {e}", exc_info=True)
            self.db_session.rollback()
            return {
                "current_month": 0,
                "vs_prev_month": None,
                "vs_3_months": None,
                "vs_12_months": None,
                "trend": "stable"
            }

    def get_all_comparison_metrics_batch(self, client_id: str) -> dict:
        """
        Get comparison metrics for ALL indicator types in a SINGLE database query.

        This replaces 12+ separate queries with just 1 query.
        Maps chart_types to indicator types:
        - clientes_no_tempo -> customers
        - produtos_no_tempo -> products
        - pedidos_no_tempo -> orders
        - fornecedores_no_tempo -> suppliers

        Returns:
            Dict with keys 'customers', 'products', 'orders', 'suppliers', each containing
            comparison metrics (current_month, vs_prev_month, vs_3_months, vs_12_months, trend)
        """
        chart_type_mapping = {
            'clientes_no_tempo': 'customers',
            'produtos_no_tempo': 'products',
            'pedidos_no_tempo': 'orders',
            'fornecedores_no_tempo': 'suppliers'
        }

        default_metrics = {
            "current_month": 0,
            "vs_prev_month": None,
            "vs_3_months": None,
            "vs_12_months": None,
            "trend": "stable"
        }

        try:
            result = self.db_session.execute(
                text("""
                    WITH recent_data AS (
                        SELECT
                            chart_type,
                            period_date,
                            total,
                            ROW_NUMBER() OVER (PARTITION BY chart_type ORDER BY period_date DESC) as rn
                        FROM analytics_gold_time_series
                        WHERE client_id = :client_id
                          AND chart_type IN ('clientes_no_tempo', 'produtos_no_tempo', 'pedidos_no_tempo', 'fornecedores_no_tempo')
                    )
                    SELECT
                        chart_type,
                        MAX(CASE WHEN rn = 1 THEN total END) as current_month,
                        MAX(CASE WHEN rn = 2 THEN total END) as prev_month,
                        AVG(CASE WHEN rn BETWEEN 2 AND 4 THEN total END) as avg_3_months,
                        AVG(CASE WHEN rn BETWEEN 2 AND 12 THEN total END) as avg_12_months
                    FROM recent_data
                    GROUP BY chart_type
                """),
                {"client_id": client_id}
            ).fetchall()

            metrics_by_type = {key: default_metrics.copy() for key in chart_type_mapping.values()}

            for row in result:
                indicator_key = chart_type_mapping.get(row.chart_type)
                if not indicator_key:
                    continue

                current = float(row.current_month or 0)
                prev_month = float(row.prev_month or 0)
                avg_3 = float(row.avg_3_months or 0)
                avg_12 = float(row.avg_12_months or 0)

                def calc_pct(current_val, prev_val):
                    if prev_val == 0:
                        return 100.0 if current_val > 0 else None
                    return round(((current_val - prev_val) / prev_val) * 100, 2)

                vs_prev = calc_pct(current, prev_month)
                vs_3 = calc_pct(current, avg_3)
                vs_12 = calc_pct(current, avg_12)

                values = [v for v in [vs_prev, vs_3, vs_12] if v is not None]
                if values:
                    avg_change = sum(values) / len(values)
                    trend = "up" if avg_change > 5 else ("down" if avg_change < -5 else "stable")
                else:
                    trend = "stable"

                metrics_by_type[indicator_key] = {
                    "current_month": int(current),
                    "vs_prev_month": vs_prev,
                    "vs_3_months": vs_3,
                    "vs_12_months": vs_12,
                    "trend": trend
                }

            logger.info(f"✅ Fetched comparison metrics for all indicators in single query")
            return metrics_by_type

        except Exception as e:
            logger.error(f"❌ Failed to batch fetch comparison metrics: {e}", exc_info=True)
            self.db_session.rollback()
            return {key: default_metrics.copy() for key in chart_type_mapping.values()}

    def get_gold_time_series_with_dates(self, client_id: str, dimension: str) -> list[dict]:
        """
        Retrieve detailed time-series data including period_date for filtering.

        Args:
            client_id: Client identifier
            dimension: 'orders', 'customers', 'products', or 'suppliers'

        Returns:
            List of dicts with keys: period, period_date, total, calculated_at
        """
        try:
            result = self.db_session.execute(
                text("""
                    SELECT period, period_date, total, calculated_at
                    FROM analytics_gold_time_series
                    WHERE client_id = :client_id AND dimension = :dimension
                    ORDER BY period_date ASC
                """),
                {"client_id": client_id, "dimension": dimension}
            ).fetchall()

            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"❌ Failed to read time series for dimension {dimension}: {e}", exc_info=True)
            self.db_session.rollback()  # Rollback to clear failed transaction state
            return []

    def get_gold_products_aggregated(self, client_id: str, start_date: datetime, end_date: datetime) -> dict:
        """
        Get aggregated product metrics filtered by date range.

        Filters products where ultima_venda falls within the specified period.

        Returns:
            Dict with keys: total_sold, unique_products, top_sellers, avg_price
        """
        try:
            # Get aggregated metrics
            result = self.db_session.execute(
                text("""
                    SELECT
                        COALESCE(SUM(total_quantity_sold), 0) as total_sold,
                        COUNT(DISTINCT product_name) as unique_products,
                        COALESCE(AVG(avg_price), 0) as avg_price
                    FROM analytics_gold_products
                    WHERE client_id = :client_id
                      AND ultima_venda >= :start_date
                      AND ultima_venda <= :end_date
                """),
                {"client_id": client_id, "start_date": start_date, "end_date": end_date}
            ).fetchone()

            # Get top sellers
            top_sellers_result = self.db_session.execute(
                text("""
                    SELECT product_name, total_revenue
                    FROM analytics_gold_products
                    WHERE client_id = :client_id
                      AND ultima_venda >= :start_date
                      AND ultima_venda <= :end_date
                    ORDER BY total_revenue DESC
                    LIMIT 10
                """),
                {"client_id": client_id, "start_date": start_date, "end_date": end_date}
            ).fetchall()

            return {
                "total_sold": int(result.total_sold) if result else 0,
                "unique_products": int(result.unique_products) if result else 0,
                "avg_price": float(result.avg_price) if result else 0.0,
                "top_sellers": [
                    {"name": row.product_name, "revenue": float(row.total_revenue)}
                    for row in top_sellers_result
                ],
                "low_stock_alerts": 0  # Not available in gold_products
            }
        except Exception as e:
            logger.error(f"❌ Failed to aggregate product metrics: {e}", exc_info=True)
            self.db_session.rollback()  # Rollback to clear failed transaction state
            return {
                "total_sold": 0,
                "unique_products": 0,
                "avg_price": 0.0,
                "top_sellers": [],
                "low_stock_alerts": 0
            }

    def get_gold_customers_aggregated(self, client_id: str, start_date: datetime, end_date: datetime) -> dict:
        """
        Get aggregated customer metrics filtered by date range.

        Filters customers where ultima_venda falls within the specified period.

        Returns:
            Dict with keys: total_active, new_customers, returning_customers, avg_lifetime_value
        """
        try:
            # Get aggregated metrics
            result = self.db_session.execute(
                text("""
                    SELECT
                        COUNT(*) as total_active,
                        COALESCE(AVG(lifetime_value), 0) as avg_lifetime_value
                    FROM analytics_gold_customers
                    WHERE client_id = :client_id
                      AND ultima_venda >= :start_date
                      AND ultima_venda <= :end_date
                """),
                {"client_id": client_id, "start_date": start_date, "end_date": end_date}
            ).fetchone()

            # Count new customers (primeira_venda in period)
            new_customers = self.db_session.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM analytics_gold_customers
                    WHERE client_id = :client_id
                      AND primeira_venda >= :start_date
                      AND primeira_venda <= :end_date
                """),
                {"client_id": client_id, "start_date": start_date, "end_date": end_date}
            ).fetchone()

            total_active = int(result.total_active) if result else 0
            new_count = int(new_customers.count) if new_customers else 0
            returning = max(0, total_active - new_count)

            return {
                "total_active": total_active,
                "new_customers": new_count,
                "returning_customers": returning,
                "avg_lifetime_value": float(result.avg_lifetime_value) if result else 0.0
            }
        except Exception as e:
            logger.error(f"❌ Failed to aggregate customer metrics: {e}", exc_info=True)
            self.db_session.rollback()  # Rollback to clear failed transaction state
            return {
                "total_active": 0,
                "new_customers": 0,
                "returning_customers": 0,
                "avg_lifetime_value": 0.0
            }

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
            self.db_session.rollback()  # Rollback to clear failed transaction state
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
            self.db_session.rollback()  # Rollback to clear failed transaction state
            return []

    def calculate_growth_from_time_series(self, client_id: str, chart_type: str) -> float | None:
        """
        Calculate period-over-period growth percentage from time series data.
        Returns growth % comparing last two periods (e.g., current month vs previous month).
        """
        try:
            result = self.db_session.execute(
                text("""
                    SELECT period, total
                    FROM analytics_gold_time_series
                    WHERE client_id = :client_id AND chart_type = :chart_type
                    ORDER BY period_date DESC
                    LIMIT 2
                """),
                {"client_id": client_id, "chart_type": chart_type}
            ).fetchall()

            if len(result) < 2:
                return None  # Need at least 2 periods for comparison

            current_total = result[0].total
            previous_total = result[1].total

            if previous_total == 0:
                return None

            growth = ((current_total - previous_total) / previous_total) * 100
            return round(growth, 2)

        except Exception as e:
            logger.error(f"❌ Failed to calculate growth from time series {chart_type}: {e}")
            self.db_session.rollback()  # Rollback to clear failed transaction state
            return None

