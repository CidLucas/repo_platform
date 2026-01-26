# src/analytics_api/data_access/postgres_repository.py
import logging
import json
import uuid
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import text
from analytics_api.core.analytics_mapping import get_silver_table_name
from vizu_supabase_client.client import get_supabase_client
from vizu_db_connector.database import SessionLocal

logger = logging.getLogger(__name__)

class PostgresRepository:
    """
    Data access layer using both Supabase SDK and direct SQLAlchemy.

    - Supabase SDK: For simple CRUD operations via REST API
    - SQLAlchemy: For complex queries, bulk inserts, and star schema writes

    Supports context manager for automatic session cleanup:
        with PostgresRepository() as repo:
            repo.get_dim_customers(client_id)
        # Session automatically closed
    """
    def __init__(self):
        """Initialize with both Supabase client and SQLAlchemy session."""
        self.supabase = get_supabase_client()
        self.db_session = SessionLocal()
        self._owns_session = True  # Track if we should close session

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure session is closed."""
        self.close()
        return False  # Don't suppress exceptions

    def close(self):
        """Explicitly close the database session to release connection back to pool."""
        if self.db_session and self._owns_session:
            try:
                self.db_session.close()
                logger.debug("Database session closed successfully")
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")

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
        Fetch silver data for client via direct SQL (for foreign tables) or Supabase API.

        Foreign tables (BigQuery FDW) must be queried via direct SQL since
        PostgREST doesn't expose non-public schemas or foreign tables.

        Applies column_mapping from client_data_sources to translate
        source column names to canonical names.
        """
        logger.info(f"🔄 [get_silver_dataframe] Loading silver data for client: {client_id}")

        # Load column_mapping
        column_mapping = self._get_column_mapping(client_id)
        table_name = get_silver_table_name(client_id)

        if not column_mapping:
            logger.warning(f"⚠️  No column_mapping found for client {client_id}")
            return pd.DataFrame()

        logger.info(f"🔍 Querying silver table: {table_name}")
        logger.info(f"  📝 Column mapping: {len(column_mapping)} columns")
        logger.info(f"  Sample mappings (first 5):")
        for source, canonical in list(column_mapping.items())[:5]:
            logger.info(f"    '{source}' → {canonical}")

        try:
            # Foreign tables (bigquery.*) must be queried via direct SQL
            # PostgREST doesn't expose foreign tables or non-public schemas
            if table_name.startswith("bigquery.") or "." in table_name:
                logger.info(f"  🔗 Using direct SQL for foreign table: {table_name}")
                # Format table name for SQL: bigquery.table_name -> "bigquery"."table_name"
                quoted_table = '"' + table_name.replace('.', '"."') + '"'

                # Set longer timeout for BigQuery FDW queries (5 minutes)
                # FDW queries can be slow due to network latency to BigQuery
                try:
                    self.db_session.execute(text("SET LOCAL statement_timeout = '300s'"))
                    logger.info("  ⏱️ Set statement_timeout to 300s for FDW query")
                except Exception as timeout_err:
                    logger.warning(f"  ⚠️ Could not set statement_timeout: {timeout_err}")

                result = self.db_session.execute(
                    text(f"SELECT * FROM {quoted_table}")
                )
                rows = result.fetchall()
                columns = list(result.keys())  # Convert RMKeyView to list
                logger.info(f"  📋 Foreign table columns: {columns}")
                if not rows:
                    logger.warning(f"No data found in {table_name}")
                    return pd.DataFrame()
                logger.info(f"  📊 Fetched {len(rows)} rows from foreign table")
                df = pd.DataFrame(rows, columns=columns)
            else:
                # Regular tables can use Supabase REST API
                response = (
                    self.supabase
                    .table(table_name)
                    .select("*")
                    .execute()
                )
                if not response.data:
                    logger.warning(f"No data found in {table_name}")
                    return pd.DataFrame()
                df = pd.DataFrame(response.data)

            logger.info(f"  ✓ Query returned data: {len(df)} rows, {len(df.columns)} columns")
            logger.info(f"  📊 DataFrame columns (raw): {list(df.columns)}")

            # Rename columns to canonical names
            rename_map = {}
            for source_col, canonical_col in column_mapping.items():
                if source_col in df.columns:
                    rename_map[source_col] = canonical_col
                else:
                    logger.debug(f"  ⚠️  Mapping '{source_col}' → '{canonical_col}' skipped: source not in DataFrame")

            logger.info(f"  🔄 Rename map ({len(rename_map)} mappings): {rename_map}")

            if rename_map:
                df.rename(columns=rename_map, inplace=True)
                logger.info(f"  📊 DataFrame columns (after rename): {list(df.columns)}")
                logger.info(f"  📈 Data types:")
                for col in df.columns[:10]:
                    logger.info(f"    {col}: {df[col].dtype}")

                # Log sample values from first row
                if not df.empty:
                    logger.info(f"  📍 First row sample:")
                    for col in list(df.columns)[:5]:
                        val = df[col].iloc[0]
                        logger.info(f"    {col}: {type(val).__name__} = {str(val)[:100]}")

            # FALLBACK: Generate synthetic order_id if missing
            if 'order_id' not in df.columns and not df.empty:
                logger.warning("⚠️  order_id column missing, generating synthetic IDs")
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
                    composite_key = id_components[0]
                    for component in id_components[1:]:
                        composite_key = composite_key + '_' + component

                    df['order_id'] = composite_key.apply(lambda x: str(abs(hash(x)) % 10**10))
                    logger.info(f"  ✓ Generated {len(df['order_id'].unique())} unique synthetic order_ids")
                else:
                    df['order_id'] = df.index.astype(str)
                    logger.warning(f"  ⚠️  Using row index as order_id")

            # DATA QUALITY CHECK
            if not df.empty:
                logger.info(f"[DATA QUALITY CHECK]")
                logger.info(f"  Total rows: {len(df)}")

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

            logger.info(f"✅ [get_silver_dataframe] Complete - {len(df)} rows, {len(df.columns)} columns")
            return df

        except Exception as e:
            logger.error(f"❌ Failed to load silver data: {type(e).__name__}")
            logger.error(f"  Error: {str(e)[:300]}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            raise

    def _get_column_mapping(self, client_id: str) -> dict[str, str] | None:
        """
        Loads the column_mapping from client_data_sources via Supabase API.

        Returns:
            dict mapping source column names to canonical names,
            or None if no mapping exists
        """
        try:
            logger.info(f"  Loading column_mapping from client_data_sources for client_id={client_id}...")

            # Query via Supabase API
            response = (
                self.supabase
                .table("client_data_sources")
                .select("column_mapping")
                .eq("client_id", client_id)
                .eq("storage_type", "foreign_table")
                .eq("sync_status", "active")
                .order("last_synced_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                column_mapping = response.data[0].get("column_mapping")
                if column_mapping:
                    logger.info(f"  ✓ Loaded column_mapping: {len(column_mapping)} mappings")
                    # Log all mappings
                    for source, canonical in sorted(column_mapping.items()):
                        logger.info(f"    '{source}' → {canonical}")
                    return column_mapping

            logger.warning(f"  ⚠️  No column_mapping found for client_id={client_id}")
            return None

        except Exception as e:
            logger.error(f"  ❌ Error loading column_mapping: {type(e).__name__}: {str(e)[:200]}")
            return None

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
            # Check if record exists using external_user_id via Supabase API
            response = (
                self.supabase
                .table("clientes_vizu")
                .select("client_id")
                .eq("external_user_id", external_user_id)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                # Return the existing client_id
                return str(response.data[0]["client_id"])

            # Create new record with external_user_id via Supabase upsert
            # Schema: client_id (UUID PK auto-gen), external_user_id (TEXT UNIQUE), nome_empresa, tipo_cliente, tier
            upsert_response = (
                self.supabase
                .table("clientes_vizu")
                .upsert({
                    "external_user_id": external_user_id,
                    "nome_empresa": email or "Empresa",
                    "tipo_cliente": "standard",
                    "tier": "free",
                }, on_conflict="external_user_id")
                .execute()
            )

            if upsert_response.data and len(upsert_response.data) > 0:
                created_client_id = str(upsert_response.data[0]["client_id"])
                logger.info(f"Created/updated clientes_vizu record with client_id={created_client_id} for external_user_id={external_user_id}")
                return created_client_id

            # Fallback: query again to get the client_id (in case upsert didn't return it)
            retry_response = (
                self.supabase
                .table("clientes_vizu")
                .select("client_id")
                .eq("external_user_id", external_user_id)
                .limit(1)
                .execute()
            )
            if retry_response.data and len(retry_response.data) > 0:
                return str(retry_response.data[0]["client_id"])

            raise ValueError(f"Failed to create/retrieve client_id for external_user_id={external_user_id}")

        except Exception as e:
            logger.error(f"Error ensuring clientes_vizu record: {e}", exc_info=True)
            # Return the external_user_id as fallback (not ideal but prevents total failure)
            return external_user_id

    # =====================================================
    # ANALYTICS_V2 STAR SCHEMA WRITE METHODS (NEW)
    # Dual-write to both old and new schema during testing
    # =====================================================

    def write_star_customers(self, client_id: str, customers_data: list[dict]) -> int:
        """Bulk persist customer dimension to analytics_v2.dim_customer (star schema)."""
        if not customers_data:
            return 0
        try:
            # Upsert customers for this client (avoid deleting to prevent FK violations)

            # Deduplicate by cpf_cnpj (keep last occurrence)
            seen_cpf = {}
            for customer in customers_data:
                cpf = customer.get("receiver_cpf_cnpj")
                if cpf:
                    seen_cpf[cpf] = customer
            unique_customers = list(seen_cpf.values())
            logger.info(f"  Deduped {len(customers_data)} -> {len(unique_customers)} unique customers by cpf_cnpj")

            # Prepare bulk data for star schema
            values = [
                (
                    client_id,
                    customer.get("receiver_cpf_cnpj"),
                    customer.get("nome"),
                    customer.get("receiver_telefone"),
                    customer.get("receiver_rua"),
                    customer.get("receiver_numero"),
                    customer.get("receiver_bairro"),
                    customer.get("receiver_cidade"),
                    (customer.get("estado") or customer.get("endereco_uf") or customer.get("receiverstateuf") or customer.get("receiver_uf") or None),
                    customer.get("receiver_cep"),
                )
                for customer in unique_customers
            ]

            # Bulk INSERT with ON CONFLICT DO UPDATE
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_v2.dim_customer (
                    client_id, cpf_cnpj, name, telefone,
                    endereco_rua, endereco_numero, endereco_bairro,
                    endereco_cidade, endereco_uf, endereco_cep,
                    created_at, updated_at
                ) VALUES %s
                ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
                    name = EXCLUDED.name,
                    telefone = EXCLUDED.telefone,
                    endereco_rua = EXCLUDED.endereco_rua,
                    endereco_numero = EXCLUDED.endereco_numero,
                    endereco_bairro = EXCLUDED.endereco_bairro,
                    endereco_cidade = EXCLUDED.endereco_cidade,
                    endereco_uf = EXCLUDED.endereco_uf,
                    endereco_cep = EXCLUDED.endereco_cep,
                    updated_at = NOW()
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(unique_customers)} customer records to analytics_v2.dim_customer for {client_id}")
            return len(unique_customers)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write customers to analytics_v2: {e}", exc_info=True)
            return 0

    def write_star_suppliers(self, client_id: str, suppliers_data: list[dict]) -> int:
        """Bulk persist supplier dimension to analytics_v2.dim_supplier (star schema)."""
        if not suppliers_data:
            return 0
        try:
            # Upsert suppliers for this client (avoid deleting to prevent FK violations)

            # Deduplicate by cnpj (keep last occurrence)
            seen_cnpj = {}
            for supplier in suppliers_data:
                cnpj = supplier.get("emitter_cnpj")
                if cnpj:
                    seen_cnpj[cnpj] = supplier
            unique_suppliers = list(seen_cnpj.values())
            logger.info(f"  Deduped {len(suppliers_data)} -> {len(unique_suppliers)} unique suppliers by cnpj")

            # Prepare bulk data for star schema
            values = [
                (
                    client_id,
                    supplier.get("emitter_cnpj"),
                    supplier.get("nome"),
                    supplier.get("emitter_telefone"),
                    supplier.get("emitter_cidade"),
                    supplier.get("emitter_uf"),
                )
                for supplier in unique_suppliers
            ]

            # Bulk INSERT with ON CONFLICT DO UPDATE
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_v2.dim_supplier (
                    client_id, cnpj, name, telefone,
                    endereco_cidade, endereco_uf,
                    created_at, updated_at
                ) VALUES %s
                ON CONFLICT (client_id, cnpj) DO UPDATE SET
                    name = EXCLUDED.name,
                    telefone = EXCLUDED.telefone,
                    endereco_cidade = EXCLUDED.endereco_cidade,
                    endereco_uf = EXCLUDED.endereco_uf,
                    updated_at = NOW()
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(unique_suppliers)} supplier records to analytics_v2.dim_supplier for {client_id}")
            return len(unique_suppliers)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write suppliers to analytics_v2: {e}", exc_info=True)
            return 0

    def write_star_products(self, client_id: str, products_data: list[dict]) -> int:
        """Bulk persist product dimension to analytics_v2.dim_product (star schema)."""
        if not products_data:
            return 0
        try:
            # Prepare bulk data: include product_id and aggregated metric columns
            # Expected product keys (if available): product_id, product_name/nome, categoria, ncm, cfop,
            # total_quantity_sold, total_revenue, avg_price, number_of_orders,
            # avg_quantity_per_order, frequency_per_month, recency_days, last_sale_date,
            # cluster_score, cluster_tier
            values = []
            for product in products_data:
                prod_id = product.get("product_id") or str(uuid.uuid4())
                prod_name = product.get("product_name") or product.get("nome") or product.get("raw_product_description")
                categoria = product.get("categoria")
                ncm = product.get("ncm")
                cfop = product.get("cfop")

                total_quantity_sold = self._sanitize_numeric(product.get("quantidade_total") or product.get("total_quantity_sold") or 0, default=0)
                total_revenue = self._sanitize_numeric(product.get("receita_total") or product.get("total_revenue") or 0, default=0)
                avg_price = self._sanitize_numeric(product.get("valor_unitario_medio") or product.get("avg_price") or 0, default=0)
                number_of_orders = int(product.get("num_pedidos_unicos") or product.get("number_of_orders") or 0)
                avg_quantity_per_order = self._sanitize_numeric(product.get("qtd_media_por_pedido") or product.get("avg_quantity_per_order") or 0, default=0)
                frequency_per_month = self._sanitize_numeric(product.get("frequencia_pedidos_mes") or product.get("frequency_per_month") or 0, default=0)
                recency_days = int(product.get("recencia_dias") or product.get("recency_days") or 0)
                last_sale_date = product.get("ultima_venda") or product.get("last_sale_date") or None
                cluster_score = self._sanitize_numeric(product.get("cluster_score") or 0, default=0)
                cluster_tier = str(product.get("cluster_tier") or "C")

                values.append((
                    prod_id,
                    client_id,
                    prod_name,
                    categoria,
                    ncm,
                    cfop,
                    total_quantity_sold,
                    total_revenue,
                    avg_price,
                    number_of_orders,
                    avg_quantity_per_order,
                    frequency_per_month,
                    recency_days,
                    last_sale_date,
                    cluster_score,
                    cluster_tier,
                ))

            # Bulk INSERT
            conn = self.db_session.connection().connection
            cursor = conn.cursor()
            execute_values(
                cursor,
                """
                INSERT INTO analytics_v2.dim_product (
                    product_id, client_id, product_name, categoria, ncm, cfop,
                    total_quantity_sold, total_revenue, avg_price, number_of_orders,
                    avg_quantity_per_order, frequency_per_month, recency_days, last_sale_date,
                    cluster_score, cluster_tier, created_at, updated_at
                ) VALUES %s
                ON CONFLICT (client_id, product_name) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    categoria = EXCLUDED.categoria,
                    ncm = EXCLUDED.ncm,
                    cfop = EXCLUDED.cfop,
                    total_quantity_sold = EXCLUDED.total_quantity_sold,
                    total_revenue = EXCLUDED.total_revenue,
                    avg_price = EXCLUDED.avg_price,
                    number_of_orders = EXCLUDED.number_of_orders,
                    avg_quantity_per_order = EXCLUDED.avg_quantity_per_order,
                    frequency_per_month = EXCLUDED.frequency_per_month,
                    recency_days = EXCLUDED.recency_days,
                    last_sale_date = EXCLUDED.last_sale_date,
                    cluster_score = EXCLUDED.cluster_score,
                    cluster_tier = EXCLUDED.cluster_tier,
                    updated_at = NOW()
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                page_size=1000
            )

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {len(products_data)} product records to analytics_v2.dim_product for {client_id}")
            return len(products_data)
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write products to analytics_v2: {e}", exc_info=True)
            return 0

    def write_fact_sales(self, client_id: str, invoices_data: list[dict], truncate_first: bool = True) -> int:
        """Bulk persist transactional fact table fact_sales with FK references to dimensions.

        Each invoice line item becomes one row in fact_sales.
        Uses bulk dimension lookups for performance (~1000s of rows in seconds).
        Includes retry logic for transient timeouts and batching for large datasets.

        Args:
            client_id: The client ID to write data for
            invoices_data: List of invoice dictionaries
            truncate_first: If True, delete existing fact_sales for this client before insert.
                           This is faster than UPSERT for full reloads.

        Expected invoice_data columns (mapped from source):
        - receiver_cpf_cnpj: Customer identifier
        - emitter_cnpj: Supplier identifier
        - raw_product_description: Product name
        - order_id, data_transacao, quantidade, valor_unitario, valor_total_emitter
        """
        if not invoices_data:
            return 0

        try:
            logger.info(f"📥 Preparing to write {len(invoices_data)} invoice rows to fact_sales...")

            # OPTIMIZATION: Truncate existing data for this client (faster than UPSERT)
            if truncate_first:
                logger.info(f"  🗑️  Clearing existing fact_sales for client {client_id}...")
                self.db_session.execute(
                    text("DELETE FROM analytics_v2.fact_sales WHERE client_id = :client_id"),
                    {"client_id": client_id}
                )
                self.db_session.commit()
                logger.info(f"  ✓ Cleared existing fact_sales")

            # OPTIMIZATION: Bulk load all dimension data once instead of querying per row
            logger.debug(f"  Loading dimension lookup tables...")

            # Helper to normalize cpf/cnpj for lookups (handles float vs string)
            def normalize_doc(val):
                if val is None:
                    return None
                return str(val)

            # Load all customers for this client
            customers_lookup = {}
            try:
                customer_results = self.db_session.execute(
                    text("SELECT customer_id, cpf_cnpj FROM analytics_v2.dim_customer WHERE client_id = :client_id"),
                    {"client_id": client_id}
                ).fetchall()
                for row in customer_results:
                    # Store with normalized key
                    customers_lookup[normalize_doc(row.cpf_cnpj)] = row.customer_id
                logger.info(f"    ✓ Loaded {len(customers_lookup)} customers for lookup")
            except Exception as e:
                logger.error(f"  ✗ Failed to load customers: {e}")
                raise

            # Load all suppliers for this client
            suppliers_lookup = {}
            try:
                supplier_results = self.db_session.execute(
                    text("SELECT supplier_id, cnpj FROM analytics_v2.dim_supplier WHERE client_id = :client_id"),
                    {"client_id": client_id}
                ).fetchall()
                for row in supplier_results:
                    # Store with normalized key
                    suppliers_lookup[normalize_doc(row.cnpj)] = row.supplier_id
                logger.info(f"    ✓ Loaded {len(suppliers_lookup)} suppliers for lookup")
            except Exception as e:
                logger.error(f"  ✗ Failed to load suppliers: {e}")
                raise

            # Load all products for this client
            products_lookup = {}
            try:
                product_results = self.db_session.execute(
                    text("SELECT product_id, product_name FROM analytics_v2.dim_product WHERE client_id = :client_id"),
                    {"client_id": client_id}
                ).fetchall()
                for row in product_results:
                    products_lookup[row.product_name] = row.product_id
                logger.debug(f"    ✓ Loaded {len(products_lookup)} products")
            except Exception as e:
                logger.error(f"  ✗ Failed to load products: {e}")
                raise

            # Process invoices with in-memory lookups (fast)
            logger.debug(f"  Processing {len(invoices_data)} invoice rows...")
            values = []
            failed_rows = []

            for invoice in invoices_data:
                try:
                    receiver_cpf = invoice.get("receiver_cpf_cnpj")
                    emitter_cnpj = invoice.get("emitter_cnpj")
                    product_name = invoice.get("raw_product_description")

                    # Lookup in memory (normalize keys to match DB format)
                    customer_id = customers_lookup.get(normalize_doc(receiver_cpf))
                    supplier_id = suppliers_lookup.get(normalize_doc(emitter_cnpj))
                    product_id = products_lookup.get(product_name)

                    # Skip if any dimension missing
                    if not customer_id:
                        failed_rows.append({"order_id": invoice.get("order_id"), "reason": f"Customer {receiver_cpf} not found"})
                        continue
                    if not supplier_id:
                        failed_rows.append({"order_id": invoice.get("order_id"), "reason": f"Supplier {emitter_cnpj} not found"})
                        continue
                    if not product_id:
                        failed_rows.append({"order_id": invoice.get("order_id"), "reason": f"Product '{product_name}' not found"})
                        continue

                    # Add to bulk insert list
                    values.append((
                        client_id,
                        customer_id,
                        supplier_id,
                        product_id,
                        invoice.get("order_id"),
                        invoice.get("data_transacao"),
                        float(invoice.get("quantidade", 0)),
                        float(invoice.get("valor_unitario", 0)),
                        float(invoice.get("valor_total_emitter") or invoice.get("valor_total", 0)),
                        receiver_cpf,
                        emitter_cnpj
                    ))

                except Exception as row_error:
                    failed_rows.append({"order_id": invoice.get("order_id"), "reason": str(row_error)})
                    continue

            if not values:
                # Log first few failures for debugging
                if failed_rows:
                    logger.warning(f"⚠️  No valid fact_sales rows to insert (all {len(invoices_data)} had missing dimensions)")
                    logger.warning(f"  Sample failures (first 5):")
                    for fail in failed_rows[:5]:
                        logger.warning(f"    - order_id={fail.get('order_id')}: {fail.get('reason')}")
                else:
                    logger.warning(f"⚠️  No valid fact_sales rows to insert (all {len(invoices_data)} had missing dimensions)")
                return 0

            # Bulk insert using psycopg2 for speed - batch if large dataset
            logger.debug(f"  Bulk inserting {len(values)} valid rows (in batches of 5000)...")

            batch_size = 5000
            total_inserted = 0
            max_retries = 3

            for batch_idx in range(0, len(values), batch_size):
                batch = values[batch_idx:batch_idx + batch_size]
                batch_num = (batch_idx // batch_size) + 1
                total_batches = (len(values) + batch_size - 1) // batch_size

                retry_count = 0
                while retry_count < max_retries:
                    try:
                        logger.debug(f"    Batch {batch_num}/{total_batches}: Inserting {len(batch)} rows (attempt {retry_count + 1})...")

                        conn = self.db_session.connection().connection
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
                            batch,
                            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                            page_size=1000
                        )

                        conn.commit()
                        total_inserted += len(batch)
                        logger.debug(f"    ✓ Batch {batch_num}/{total_batches} inserted successfully")
                        break

                    except Exception as batch_error:
                        retry_count += 1
                        error_msg = str(batch_error)

                        if "timeout" in error_msg.lower() and retry_count < max_retries:
                            import time
                            wait_time = 2 ** retry_count  # Exponential backoff: 2s, 4s, 8s
                            logger.warning(f"  ⚠️  Query timeout on batch {batch_num} (attempt {retry_count}), retrying in {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"  ✗ Batch {batch_num} failed after {retry_count} attempts: {batch_error}")
                            raise

            self.db_session.commit()
            logger.info(f"✓ Bulk wrote {total_inserted} fact_sales records to analytics_v2.fact_sales for {client_id}")

            if failed_rows:
                logger.warning(f"⚠️  {len(failed_rows)} fact_sales inserts skipped due to missing dimensions:")
                for failed in failed_rows[:5]:
                    logger.debug(f"   - {failed['order_id']}: {failed['reason']}")

            return total_inserted

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"❌ Failed to bulk write fact_sales to analytics_v2: {e}", exc_info=True)
            return 0

    def write_star_time_series(self, client_id: str, chart_data: list[dict]) -> int:
        """Skip writing - time series data is now computed from v_time_series view."""
        if not chart_data:
            return 0
        logger.info(f"⊗ Skipping write_star_time_series for {client_id} - data available via v_time_series view ({len(chart_data)} items)")
        return len(chart_data)

    def write_star_regional(self, client_id: str, chart_data: list[dict]) -> int:
        """Skip writing - regional data is now computed from v_regional view."""
        if not chart_data:
            return 0
        logger.info(f"⊗ Skipping write_star_regional for {client_id} - data available via v_regional view ({len(chart_data)} items)")
        return len(chart_data)

    def write_star_last_orders(self, client_id: str, orders_data: list[dict]) -> int:
        """Skip writing - last orders data is now computed from v_last_orders view."""
        if not orders_data:
            return 0
        logger.info(f"⊗ Skipping write_star_last_orders for {client_id} - data available via v_last_orders view ({len(orders_data)} items)")
        return len(orders_data)

    def write_star_customer_products(self, client_id: str, customer_products_data: list[dict]) -> int:
        """Skip writing - customer-product data is now computed from v_customer_products view."""
        if not customer_products_data:
            return 0
        logger.info(f"⊗ Skipping write_star_customer_products for {client_id} - data available via v_customer_products view ({len(customer_products_data)} items)")
        return len(customer_products_data)

    # ---
    # V2 Read Methods (Star Schema)
    # ---

    # =====================================================
    # ANALYTICS_V2 STAR SCHEMA READ METHODS (NEW)
    # =====================================================

    def get_v2_time_series(self, client_id: str, chart_type: str) -> list[dict]:
        """Retrieve time-series chart data from v_time_series view (computed from fact_sales)."""
        try:
            # Query v_time_series materialized view (computed from fact_sales)
            result = self.db_session.execute(
                text("""
                    SELECT period AS name, total
                    FROM analytics_v2.v_time_series
                    WHERE client_id = :client_id AND chart_type = :chart_type
                    ORDER BY period_date ASC
                """),
                {"client_id": client_id, "chart_type": chart_type}
            ).fetchall()

            if result:
                logger.debug(f"📊 Read {len(result)} time_series from v_time_series for {chart_type}")
                return [{"name": row.name, "total": int(row.total)} for row in result]

            # If view is empty, return empty list
            logger.debug(f"⚠️  v_time_series empty for {chart_type}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to read v_time_series {chart_type}: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_v2_regional(self, client_id: str, chart_type: str) -> list[dict]:
        """Retrieve regional breakdown from v_regional view (computed from fact_sales)."""
        try:
            # Query v_regional materialized view (computed from fact_sales)
            result = self.db_session.execute(
                text("""
                    SELECT region_name AS name, total, contagem, percentual
                    FROM analytics_v2.v_regional
                    WHERE client_id = :client_id AND chart_type = :chart_type
                    ORDER BY total DESC
                """),
                {"client_id": client_id, "chart_type": chart_type}
            ).fetchall()

            if result:
                logger.debug(f"📊 Read {len(result)} regional from v_regional for {chart_type}")
                return [
                    {
                        "name": row.name,
                        "total": int(row.total),
                        "contagem": int(row.contagem),
                        "percentual": float(row.percentual)
                    }
                    for row in result
                ]

            # Fallback: return empty if view is empty
            logger.debug(f"⚠️  v_regional empty for {chart_type}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to read v_regional {chart_type}: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_v2_last_orders(self, client_id: str, limit: int = 20) -> list[dict]:
        """Retrieve last orders from v_last_orders view (computed from fact_sales)."""
        try:
            # Query v_last_orders materialized view (computed from fact_sales)
            result = self.db_session.execute(
                text("""
                    SELECT order_id, data_transacao, customer_cpf_cnpj, ticket_pedido, qtd_produtos
                    FROM analytics_v2.v_last_orders
                    WHERE client_id = :client_id
                    ORDER BY order_rank ASC
                    LIMIT :limit
                """),
                {"client_id": client_id, "limit": limit}
            ).fetchall()

            if result:
                logger.debug(f"📊 Read {len(result)} last_orders from v_last_orders")
                return [
                    {
                        "order_id": row.order_id,
                        "data_transacao": row.data_transacao,
                        "id_cliente": row.customer_cpf_cnpj,
                        "ticket_pedido": float(row.ticket_pedido),
                        "qtd_produtos": int(row.qtd_produtos)
                    }
                    for row in result
                ]

            # Fallback: return empty if view is empty
            logger.debug(f"⚠️  v_last_orders empty")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to read v_last_orders: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_v2_customer_products(self, client_id: str, customer_cpf_cnpj: str, limit: int = 10) -> list[dict]:
        """Retrieve customer-product data from v_customer_products view (computed from fact_sales)."""
        try:
            # Query v_customer_products materialized view (computed from fact_sales)
            result = self.db_session.execute(
                text("""
                    SELECT product_name, valor_total as receita_total, quantidade_total, num_purchases as num_pedidos,
                           CASE WHEN quantidade_total > 0 THEN valor_total / quantidade_total ELSE 0 END as valor_unitario_medio
                    FROM analytics_v2.v_customer_products
                    WHERE client_id = :client_id AND customer_cpf_cnpj = :customer_cpf_cnpj
                    ORDER BY valor_total DESC
                    LIMIT :limit
                """),
                {"client_id": client_id, "customer_cpf_cnpj": customer_cpf_cnpj, "limit": limit}
            ).fetchall()

            if result:
                logger.debug(f"📊 Read {len(result)} customer_products from v_customer_products for {customer_cpf_cnpj}")
                return [
                    {
                        "product_name": row.product_name,
                        "receita_total": float(row.receita_total),
                        "quantidade_total": float(row.quantidade_total),
                        "num_pedidos": int(row.num_pedidos),
                        "valor_unitario_medio": float(row.valor_unitario_medio)
                    }
                    for row in result
                ]

            # Fallback: return empty if view is empty
            logger.debug(f"⚠️  v_customer_products empty for {customer_cpf_cnpj}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to read v_customer_products: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    # =====================================================
    # STAR SCHEMA READ METHODS (analytics_v2)
    # These methods read directly from the star schema
    # dimension and fact tables - NO silver data access
    # =====================================================

    def _get_period_days(self, period: str) -> int | None:
        """Convert period string to number of days for filtering."""
        period_map = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 365,
            "all": None,
        }
        return period_map.get(period)

    def get_dim_customers(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Read customer metrics from analytics_v2.dim_customer.

        When period != "all", filters to customers with activity in that period
        by joining with fact_sales and re-aggregating metrics.
        """
        try:
            period_days = self._get_period_days(period)

            if period_days is None:
                # No period filter - return all customers with lifetime metrics
                query = text("""
                    SELECT
                        customer_id,
                        client_id,
                        cpf_cnpj as customer_cpf_cnpj,
                        name as customer_name,
                        telefone,
                        endereco_rua,
                        endereco_numero,
                        endereco_bairro,
                        endereco_cidade,
                        endereco_uf,
                        endereco_cep,
                        total_orders,
                        total_revenue,
                        avg_order_value,
                        total_quantity,
                        orders_last_30_days,
                        frequency_per_month,
                        recency_days,
                        lifetime_start_date as primeira_venda,
                        lifetime_end_date as ultima_venda,
                        total_revenue as lifetime_value,
                        avg_order_value as ticket_medio,
                        total_orders as num_pedidos_unicos,
                        total_quantity / NULLIF(total_orders, 0) as qtd_media_por_pedido,
                        CASE WHEN recency_days <= 30 THEN 100 WHEN recency_days <= 90 THEN 75 WHEN recency_days <= 180 THEN 50 ELSE 25 END as score_r,
                        LEAST(frequency_per_month * 10, 100) as score_f,
                        CASE WHEN total_revenue >= 100000 THEN 100 WHEN total_revenue >= 50000 THEN 75 WHEN total_revenue >= 10000 THEN 50 ELSE 25 END as score_m,
                        created_at,
                        updated_at
                    FROM analytics_v2.dim_customer
                    WHERE client_id = :client_id
                    ORDER BY total_revenue DESC
                """)
                result = self.db_session.execute(query, {"client_id": client_id})
            else:
                # Period filter - aggregate from fact_sales for the period
                query = text("""
                    SELECT
                        c.customer_id,
                        c.client_id,
                        c.cpf_cnpj as customer_cpf_cnpj,
                        c.name as customer_name,
                        c.telefone,
                        c.endereco_rua,
                        c.endereco_numero,
                        c.endereco_bairro,
                        c.endereco_cidade,
                        c.endereco_uf,
                        c.endereco_cep,
                        COUNT(DISTINCT f.order_id) as total_orders,
                        COALESCE(SUM(f.valor_total), 0) as total_revenue,
                        COALESCE(AVG(f.valor_total), 0) as avg_order_value,
                        COALESCE(SUM(f.quantidade), 0) as total_quantity,
                        COUNT(DISTINCT f.order_id) as orders_last_30_days,
                        c.frequency_per_month,
                        EXTRACT(DAY FROM NOW() - MAX(f.data_transacao))::int as recency_days,
                        MIN(f.data_transacao) as primeira_venda,
                        MAX(f.data_transacao) as ultima_venda,
                        COALESCE(SUM(f.valor_total), 0) as lifetime_value,
                        COALESCE(AVG(f.valor_total), 0) as ticket_medio,
                        COUNT(DISTINCT f.order_id) as num_pedidos_unicos,
                        COALESCE(SUM(f.quantidade), 0) / NULLIF(COUNT(DISTINCT f.order_id), 0) as qtd_media_por_pedido,
                        CASE WHEN EXTRACT(DAY FROM NOW() - MAX(f.data_transacao)) <= 30 THEN 100
                             WHEN EXTRACT(DAY FROM NOW() - MAX(f.data_transacao)) <= 90 THEN 75
                             WHEN EXTRACT(DAY FROM NOW() - MAX(f.data_transacao)) <= 180 THEN 50
                             ELSE 25 END as score_r,
                        LEAST(c.frequency_per_month * 10, 100) as score_f,
                        CASE WHEN SUM(f.valor_total) >= 100000 THEN 100
                             WHEN SUM(f.valor_total) >= 50000 THEN 75
                             WHEN SUM(f.valor_total) >= 10000 THEN 50
                             ELSE 25 END as score_m,
                        c.created_at,
                        c.updated_at
                    FROM analytics_v2.dim_customer c
                    INNER JOIN analytics_v2.fact_sales f ON c.customer_id = f.customer_id
                    WHERE c.client_id = :client_id
                      AND f.data_transacao >= NOW() - INTERVAL :period_days
                    GROUP BY c.customer_id, c.client_id, c.cpf_cnpj, c.name, c.telefone,
                             c.endereco_rua, c.endereco_numero, c.endereco_bairro,
                             c.endereco_cidade, c.endereco_uf, c.endereco_cep,
                             c.frequency_per_month, c.created_at, c.updated_at
                    ORDER BY total_revenue DESC
                """)
                # Bind period as an interval string (e.g. '30 days')
                result = self.db_session.execute(query, {"client_id": client_id, "period_days": f"{period_days} days"})

            rows = result.fetchall()
            columns = result.keys()

            customers = []
            for row in rows:
                customer = dict(zip(columns, row))
                # Calculate cluster score and tier
                score_r = customer.get('score_r', 0) or 0
                score_f = customer.get('score_f', 0) or 0
                score_m = customer.get('score_m', 0) or 0
                cluster_score = (score_r + score_f + score_m) / 3
                customer['cluster_score'] = cluster_score
                customer['cluster_tier'] = 'A' if cluster_score >= 70 else 'B' if cluster_score >= 40 else 'C'
                customers.append(customer)

            logger.info(f"✓ Loaded {len(customers)} customers from analytics_v2.dim_customer")
            return customers

        except Exception as e:
            logger.error(f"❌ Failed to get customers from star schema: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_dim_suppliers(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Read supplier metrics from analytics_v2.dim_supplier.

        The dim_supplier table has pre-aggregated metrics updated by triggers:
        - total_orders_received, total_revenue, avg_order_value
        - total_products_supplied, frequency_per_month, recency_days
        """
        try:
            query = text("""
                SELECT
                    supplier_id,
                    client_id,
                    cnpj,
                    name,
                    telefone,
                    endereco_cidade,
                    endereco_uf,
                    total_orders_received as total_orders,
                    total_revenue,
                    avg_order_value,
                    avg_order_value as ticket_medio,
                    total_products_supplied,
                    frequency_per_month,
                    frequency_per_month as frequencia_pedidos_mes,
                    recency_days,
                    first_transaction_date,
                    last_transaction_date,
                    -- Compute derived metrics
                    0 as qtd_media_por_pedido,
                    -- Cluster scoring
                    CASE
                        WHEN recency_days <= 30 THEN 100
                        WHEN recency_days <= 90 THEN 75
                        WHEN recency_days <= 180 THEN 50
                        ELSE 25
                    END as score_r,
                    LEAST(frequency_per_month * 10, 100) as score_f,
                    CASE
                        WHEN total_revenue >= 100000 THEN 100
                        WHEN total_revenue >= 50000 THEN 75
                        WHEN total_revenue >= 10000 THEN 50
                        ELSE 25
                    END as score_m,
                    created_at,
                    updated_at
                FROM analytics_v2.dim_supplier
                WHERE client_id = :client_id
                ORDER BY total_revenue DESC
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            rows = result.fetchall()
            columns = result.keys()

            suppliers = []
            for row in rows:
                supplier = dict(zip(columns, row))
                # Calculate cluster score and tier
                score_r = supplier.get('score_r', 0) or 0
                score_f = supplier.get('score_f', 0) or 0
                score_m = supplier.get('score_m', 0) or 0
                cluster_score = (score_r + score_f + score_m) / 3
                supplier['cluster_score'] = cluster_score
                supplier['cluster_tier'] = 'A' if cluster_score >= 70 else 'B' if cluster_score >= 40 else 'C'
                suppliers.append(supplier)

            logger.info(f"✓ Loaded {len(suppliers)} suppliers from analytics_v2.dim_supplier")
            return suppliers

        except Exception as e:
            logger.error(f"❌ Failed to get suppliers from star schema: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_dim_products(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Read product metrics from analytics_v2.dim_product.

        When period != "all", filters to products with sales in that period
        by joining with fact_sales and re-aggregating metrics.
        """
        try:
            period_days = self._get_period_days(period)

            if period_days is None:
                # No period filter - return all products with lifetime metrics
                query = text("""
                    SELECT
                        product_id,
                        client_id,
                        product_name,
                        categoria,
                        ncm,
                        cfop,
                        total_quantity_sold,
                        total_revenue,
                        avg_price,
                        number_of_orders,
                        avg_quantity_per_order,
                        frequency_per_month,
                        recency_days,
                        last_sale_date,
                        cluster_score,
                        cluster_tier,
                        created_at,
                        updated_at
                    FROM analytics_v2.dim_product
                    WHERE client_id = :client_id
                    ORDER BY total_revenue DESC
                """)
                result = self.db_session.execute(query, {"client_id": client_id})
            else:
                # Period filter - aggregate from fact_sales for the period
                query = text("""
                    SELECT
                        p.product_id,
                        p.client_id,
                        p.product_name,
                        p.categoria,
                        p.ncm,
                        p.cfop,
                        COALESCE(SUM(f.quantidade), 0) as total_quantity_sold,
                        COALESCE(SUM(f.valor_total), 0) as total_revenue,
                        COALESCE(AVG(f.valor_unitario), 0) as avg_price,
                        COUNT(DISTINCT f.order_id) as number_of_orders,
                        COALESCE(SUM(f.quantidade), 0) / NULLIF(COUNT(DISTINCT f.order_id), 0) as avg_quantity_per_order,
                        p.frequency_per_month,
                        EXTRACT(DAY FROM NOW() - MAX(f.data_transacao))::int as recency_days,
                        MAX(f.data_transacao) as last_sale_date,
                        p.cluster_score,
                        p.cluster_tier,
                        p.created_at,
                        p.updated_at
                    FROM analytics_v2.dim_product p
                    INNER JOIN analytics_v2.fact_sales f ON p.product_id = f.product_id
                    WHERE p.client_id = :client_id
                      AND f.data_transacao >= NOW() - INTERVAL :period_days DAY
                    GROUP BY p.product_id, p.client_id, p.product_name, p.categoria,
                             p.ncm, p.cfop, p.frequency_per_month, p.cluster_score,
                             p.cluster_tier, p.created_at, p.updated_at
                    ORDER BY total_revenue DESC
                """)
                result = self.db_session.execute(query, {"client_id": client_id, "period_days": f"{period_days} days"})

            rows = result.fetchall()
            columns = result.keys()

            products = [dict(zip(columns, row)) for row in rows]
            logger.info(f"✓ Loaded {len(products)} products from analytics_v2.dim_product (period={period})")
            return products

        except Exception as e:
            logger.error(f"❌ Failed to get products from star schema: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_fact_sales_aggregated(self, client_id: str, period: str = "all") -> list[dict]:
        """
        Read order metrics from analytics_v2.fact_sales aggregated by order_id.

        Returns one row per order with aggregated line items.
        """
        try:
            period_days = self._get_period_days(period)

            query = text("""
                SELECT
                    f.order_id,
                    f.client_id,
                    f.data_transacao,
                    f.customer_cpf_cnpj,
                    c.name as customer_name,
                    f.supplier_cnpj,
                    s.name as supplier_name,
                    COUNT(*) as line_items,
                    SUM(f.quantidade) as total_quantity,
                    SUM(f.valor_total) as total_value,
                    AVG(f.valor_unitario) as avg_unit_price
                FROM analytics_v2.fact_sales f
                LEFT JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                LEFT JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                WHERE f.client_id = :client_id
                     AND f.data_transacao >= NOW() - INTERVAL :period_days DAY
                GROUP BY f.order_id, f.client_id, f.data_transacao,
                         f.customer_cpf_cnpj, c.name, f.supplier_cnpj, s.name
                ORDER BY f.data_transacao DESC
                LIMIT 1000
            """)

            result = self.db_session.execute(query, {"client_id": client_id, "period_days": f"{period_days} days"})
            rows = result.fetchall()
            columns = result.keys()

            orders = [dict(zip(columns, row)) for row in rows]
            logger.info(f"✓ Loaded {len(orders)} orders from analytics_v2.fact_sales")
            return orders

        except Exception as e:
            logger.error(f"❌ Failed to get orders from star schema: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_distinct_products(self, client_id: str) -> list[dict]:
        """Get distinct product names for filter dropdowns."""
        try:
            query = text("""
                SELECT DISTINCT product_name, product_id
                FROM analytics_v2.dim_product
                WHERE client_id = :client_id
                ORDER BY product_name
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            products = [{"product_name": row[0], "product_id": str(row[1])} for row in result.fetchall()]
            logger.info(f"✓ Loaded {len(products)} distinct products for filters")
            return products

        except Exception as e:
            logger.error(f"❌ Failed to get distinct products: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_distinct_customers(self, client_id: str) -> list[dict]:
        """Get distinct customer names for filter dropdowns."""
        try:
            query = text("""
                SELECT DISTINCT name, cpf_cnpj, customer_id
                FROM analytics_v2.dim_customer
                WHERE client_id = :client_id
                ORDER BY name
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            customers = [
                {"name": row[0], "cpf_cnpj": row[1], "customer_id": str(row[2])}
                for row in result.fetchall()
            ]
            logger.info(f"✓ Loaded {len(customers)} distinct customers for filters")
            return customers

        except Exception as e:
            logger.error(f"❌ Failed to get distinct customers: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_customers_by_product(self, client_id: str, product_name: str, period: str = "all", limit: int = 50) -> list[dict]:
        """Get customers who purchased a specific product."""
        try:
            period_days = self._get_period_days(period)

            query = text("""
                SELECT
                    c.customer_id,
                    c.name,
                    c.cpf_cnpj,
                    c.endereco_cidade,
                    c.endereco_uf,
                    SUM(f.quantidade) as quantity_purchased,
                    SUM(f.valor_total) as total_spent,
                    COUNT(DISTINCT f.order_id) as order_count,
                    MAX(f.data_transacao) as last_purchase
                FROM analytics_v2.fact_sales f
                JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                WHERE f.client_id = :client_id
                      AND f.data_transacao >= NOW() - INTERVAL :period_days DAY

                  AND p.product_name = :product_name
                GROUP BY c.customer_id, c.name, c.cpf_cnpj, c.endereco_cidade, c.endereco_uf
                ORDER BY total_spent DESC
                LIMIT :limit
            """)

            result = self.db_session.execute(query, {
                "client_id": client_id,
                "product_name": product_name,
                "limit": limit,
                "period_days": f"{period_days} days"
            })
            rows = result.fetchall()
            columns = result.keys()

            customers = [dict(zip(columns, row)) for row in rows]
            logger.info(f"✓ Found {len(customers)} customers for product '{product_name}'")
            return customers

        except Exception as e:
            logger.error(f"❌ Failed to get customers by product: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_customer_monthly_orders(self, client_id: str, customer_cpf_cnpj: str) -> list[dict]:
        """Get monthly order history for a specific customer."""
        try:
            query = text("""
                SELECT
                    DATE_TRUNC('month', f.data_transacao) as month,
                    COUNT(DISTINCT f.order_id) as order_count,
                    SUM(f.quantidade) as total_quantity,
                    SUM(f.valor_total) as total_value,
                    AVG(f.valor_total) as avg_order_value
                FROM analytics_v2.fact_sales f
                WHERE f.client_id = :client_id
                  AND f.customer_cpf_cnpj = :customer_cpf_cnpj
                GROUP BY DATE_TRUNC('month', f.data_transacao)
                ORDER BY month DESC
                LIMIT 24
            """)

            result = self.db_session.execute(query, {
                "client_id": client_id,
                "customer_cpf_cnpj": customer_cpf_cnpj
            })
            rows = result.fetchall()
            columns = result.keys()

            raw_monthly = [dict(zip(columns, row)) for row in rows]

            # Normalize to frontend contract: { month: 'YYYY-MM', num_pedidos: <int>, total_quantity, total_value, avg_order_value }
            monthly_data = []
            for r in raw_monthly:
                m = r.get('month')
                if hasattr(m, 'strftime'):
                    month_str = m.strftime('%Y-%m')
                else:
                    # fallback to string, take first 7 chars YYYY-MM
                    month_str = str(m)[:7]

                monthly_data.append({
                    'month': month_str,
                    'num_pedidos': int(r.get('order_count') or 0),
                    'total_quantity': float(r.get('total_quantity') or 0),
                    'total_value': float(r.get('total_value') or 0),
                    'avg_order_value': float(r.get('avg_order_value') or 0),
                })

            logger.info(f"✓ Loaded {len(monthly_data)} months of data for customer {customer_cpf_cnpj}")
            return monthly_data

        except Exception as e:
            logger.error(f"❌ Failed to get customer monthly orders: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def calculate_growth_from_time_series(self, client_id: str, chart_type: str) -> float:
        """
        Calculate growth percentage from time series data.
        Compares current period to previous period.
        """
        try:
            time_series = self.get_v2_time_series(client_id, chart_type)

            if len(time_series) < 2:
                return 0.0

            # Get last two periods
            current = time_series[-1].get('total', 0) or 0
            previous = time_series[-2].get('total', 0) or 0

            if previous == 0:
                return 100.0 if current > 0 else 0.0

            growth = ((current - previous) / previous) * 100
            return round(growth, 2)

        except Exception as e:
            logger.error(f"❌ Failed to calculate growth: {e}", exc_info=True)
            return 0.0

    def get_customer_detail(self, client_id: str, customer_name: str) -> dict | None:
        """Get detailed customer info by name."""
        try:
            query = text("""
                SELECT
                    customer_id,
                    client_id,
                    cpf_cnpj,
                    name,
                    telefone,
                    endereco_rua,
                    endereco_numero,
                    endereco_bairro,
                    endereco_cidade,
                    endereco_uf,
                    endereco_cep,
                    total_orders,
                    total_revenue,
                    avg_order_value,
                    total_quantity,
                    orders_last_30_days,
                    frequency_per_month,
                    recency_days,
                    lifetime_start_date,
                    lifetime_end_date,
                    created_at,
                    updated_at
                FROM analytics_v2.dim_customer
                WHERE client_id = :client_id
                  AND name = :customer_name
                LIMIT 1
            """)

            result = self.db_session.execute(query, {
                "client_id": client_id,
                "customer_name": customer_name
            })
            row = result.fetchone()

            if row:
                columns = result.keys()
                return dict(zip(columns, row))
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get customer detail: {e}", exc_info=True)
            self.db_session.rollback()
            return None

    def get_supplier_detail(self, client_id: str, supplier_name: str) -> dict | None:
        """Get detailed supplier info by name."""
        try:
            query = text("""
                SELECT
                    supplier_id,
                    client_id,
                    cnpj,
                    name,
                    telefone,
                    endereco_cidade,
                    endereco_uf,
                    total_orders_received,
                    total_revenue,
                    avg_order_value,
                    total_products_supplied,
                    frequency_per_month,
                    recency_days,
                    first_transaction_date,
                    last_transaction_date,
                    created_at,
                    updated_at
                FROM analytics_v2.dim_supplier
                WHERE client_id = :client_id
                  AND name = :supplier_name
                LIMIT 1
            """)

            result = self.db_session.execute(query, {
                "client_id": client_id,
                "supplier_name": supplier_name
            })
            row = result.fetchone()

            if row:
                columns = result.keys()
                return dict(zip(columns, row))
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get supplier detail: {e}", exc_info=True)
            self.db_session.rollback()
            return None

    def get_product_detail(self, client_id: str, product_name: str) -> dict | None:
        """Get detailed product info by name."""
        try:
            query = text("""
                SELECT
                    product_id,
                    client_id,
                    product_name,
                    categoria,
                    ncm,
                    cfop,
                    total_quantity_sold,
                    total_revenue,
                    avg_price,
                    number_of_orders,
                    avg_quantity_per_order,
                    frequency_per_month,
                    recency_days,
                    last_sale_date,
                    cluster_score,
                    cluster_tier,
                    created_at,
                    updated_at
                FROM analytics_v2.dim_product
                WHERE client_id = :client_id
                  AND product_name = :product_name
                LIMIT 1
            """)

            result = self.db_session.execute(query, {
                "client_id": client_id,
                "product_name": product_name
            })
            row = result.fetchone()

            if row:
                columns = result.keys()
                return dict(zip(columns, row))
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get product detail: {e}", exc_info=True)
            self.db_session.rollback()
            return None

    def get_last_orders(self, client_id: str, limit: int = 10) -> list[dict]:
        """Get the most recent orders."""
        try:
            query = text("""
                SELECT
                    f.order_id,
                    f.data_transacao,
                    c.name as customer_name,
                    f.customer_cpf_cnpj,
                    s.name as supplier_name,
                    SUM(f.valor_total) as total_value,
                    SUM(f.quantidade) as total_quantity,
                    COUNT(*) as line_items
                FROM analytics_v2.fact_sales f
                LEFT JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                LEFT JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                WHERE f.client_id = :client_id
                GROUP BY f.order_id, f.data_transacao, c.name, f.customer_cpf_cnpj, s.name
                ORDER BY f.data_transacao DESC
                LIMIT :limit
            """)

            result = self.db_session.execute(query, {"client_id": client_id, "limit": limit})
            rows = result.fetchall()
            columns = result.keys()

            orders = [dict(zip(columns, row)) for row in rows]
            logger.info(f"✓ Loaded {len(orders)} recent orders")
            return orders

        except Exception as e:
            logger.error(f"❌ Failed to get last orders: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_dashboard_summary(self, client_id: str) -> dict:
        """Get summary metrics for the dashboard home page."""
        try:
            query = text("""
                SELECT
                    (SELECT COUNT(*) FROM analytics_v2.dim_customer WHERE client_id = :client_id) as total_customers,
                    (SELECT COUNT(*) FROM analytics_v2.dim_supplier WHERE client_id = :client_id) as total_suppliers,
                    (SELECT COUNT(*) FROM analytics_v2.dim_product WHERE client_id = :client_id) as total_products,
                    (SELECT COUNT(DISTINCT order_id) FROM analytics_v2.fact_sales WHERE client_id = :client_id) as total_orders,
                    (SELECT COALESCE(SUM(valor_total), 0) FROM analytics_v2.fact_sales WHERE client_id = :client_id) as total_revenue,
                    (SELECT COALESCE(SUM(quantidade), 0) FROM analytics_v2.fact_sales WHERE client_id = :client_id) as total_quantity
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            row = result.fetchone()

            if row:
                return {
                    "total_customers": row[0] or 0,
                    "total_suppliers": row[1] or 0,
                    "total_products": row[2] or 0,
                    "total_orders": row[3] or 0,
                    "total_revenue": float(row[4] or 0),
                    "total_quantity": float(row[5] or 0)
                }
            return {}

        except Exception as e:
            logger.error(f"❌ Failed to get dashboard summary: {e}", exc_info=True)
            self.db_session.rollback()
            return {}

    # =====================================================
    # INDICATOR SERVICE METHODS (for time-filtered queries)
    # These support the /indicators/* endpoints
    # =====================================================

    def get_fact_sales_time_series(self, client_id: str) -> list[dict]:
        """
        Get monthly time series data from fact_sales for indicator calculations.
        Returns monthly aggregates: total_orders, total_revenue, etc.
        """
        try:
            query = text("""
                SELECT
                    DATE_TRUNC('month', data_transacao) as month,
                    COUNT(DISTINCT order_id) as total_orders,
                    SUM(valor_total) as total_revenue,
                    SUM(quantidade) as total_quantity,
                    AVG(valor_total) as avg_order_value
                FROM analytics_v2.fact_sales
                WHERE client_id = :client_id
                  AND data_transacao IS NOT NULL
                GROUP BY DATE_TRUNC('month', data_transacao)
                ORDER BY month DESC
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            rows = result.fetchall()
            columns = result.keys()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"❌ Failed to get fact_sales time series: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_dim_products_aggregated(
        self, client_id: str, start_date=None, end_date=None
    ) -> dict:
        """
        Get aggregated product metrics from dim_product, optionally filtered by date.
        Used by indicator service for product KPIs.
        """
        try:
            # Base query from dim_product
            query = text("""
                SELECT
                    COUNT(*) as unique_products,
                    COALESCE(SUM(total_quantity_sold), 0) as total_sold,
                    COALESCE(AVG(avg_price), 0) as avg_price,
                    COALESCE(SUM(total_revenue), 0) as total_revenue
                FROM analytics_v2.dim_product
                WHERE client_id = :client_id
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            row = result.fetchone()

            # Get top sellers
            top_query = text("""
                SELECT product_name, total_revenue, total_quantity_sold
                FROM analytics_v2.dim_product
                WHERE client_id = :client_id
                ORDER BY total_revenue DESC
                LIMIT 10
            """)
            top_result = self.db_session.execute(top_query, {"client_id": client_id})
            top_sellers = [
                {"name": r[0], "revenue": float(r[1] or 0), "quantity": float(r[2] or 0)}
                for r in top_result.fetchall()
            ]

            return {
                "unique_products": row[0] or 0,
                "total_sold": int(row[1] or 0),  # Must be int per ProductMetrics schema
                "avg_price": float(row[2] or 0),
                "total_revenue": float(row[3] or 0),
                "top_sellers": top_sellers,
                "low_stock_alerts": 0  # Not tracked in star schema
            }

        except Exception as e:
            logger.error(f"❌ Failed to get dim_products aggregated: {e}", exc_info=True)
            self.db_session.rollback()
            return {}

    def get_dim_customers_aggregated(
        self, client_id: str, start_date=None, end_date=None
    ) -> dict:
        """
        Get aggregated customer metrics from dim_customer, optionally filtered by date.
        Used by indicator service for customer KPIs.
        """
        try:
            query = text("""
                SELECT
                    COUNT(*) as total_active,
                    COUNT(CASE WHEN total_orders = 1 THEN 1 END) as new_customers,
                    COUNT(CASE WHEN total_orders > 1 THEN 1 END) as returning_customers,
                    COALESCE(AVG(total_revenue), 0) as avg_lifetime_value
                FROM analytics_v2.dim_customer
                WHERE client_id = :client_id
            """)

            result = self.db_session.execute(query, {"client_id": client_id})
            row = result.fetchone()

            return {
                "total_active": row[0] or 0,
                "new_customers": row[1] or 0,
                "returning_customers": row[2] or 0,
                "avg_lifetime_value": float(row[3] or 0)
            }

        except Exception as e:
            logger.error(f"❌ Failed to get dim_customers aggregated: {e}", exc_info=True)
            self.db_session.rollback()
            return {}

    # Aliases for backward compatibility with indicator_service
    def get_gold_orders_time_series(self, client_id: str) -> list[dict]:
        """Alias for get_fact_sales_time_series (backward compatibility)."""
        return self.get_fact_sales_time_series(client_id)

    def get_gold_products_aggregated(self, client_id: str, start_date=None, end_date=None) -> dict:
        """Alias for get_dim_products_aggregated (backward compatibility)."""
        return self.get_dim_products_aggregated(client_id, start_date, end_date)

    def get_gold_customers_aggregated(self, client_id: str, start_date=None, end_date=None) -> dict:
        """Alias for get_dim_customers_aggregated (backward compatibility)."""
        return self.get_dim_customers_aggregated(client_id, start_date, end_date)

    # =========================================================================
    # Materialized Views - Fast pre-computed aggregations for dashboards
    # =========================================================================

    def get_mv_customer_summary(self, client_id: str) -> list[dict]:
        """
        Read from mv_customer_summary materialized view.
        Fast pre-computed customer aggregations for dashboard.

        Returns: List of customer summaries with:
        - customer_id, name, cpf_cnpj, estado
        - total_orders, lifetime_value, avg_order_value
        - total_quantity, last_order_date, first_order_date
        - days_since_last_order
        """
        try:
            # Prefer pre-computed materialized view, but the view schema has changed
            # in some deployments (uses `estado`) while dim_customer uses `endereco_uf`.
            # To be resilient, LEFT JOIN the dim_customer table and prefer the
            # materialized view's `estado`, falling back to `endereco_uf`.
            query = text("""
                SELECT
                    m.customer_id,
                    m.name,
                    m.cpf_cnpj,
                    COALESCE(m.estado, d.endereco_uf) AS estado,
                    COALESCE(m.total_orders, 0) as total_orders,
                    COALESCE(m.lifetime_value, 0) as lifetime_value,
                    COALESCE(m.avg_order_value, 0) as avg_order_value,
                    COALESCE(m.total_quantity, 0) as total_quantity,
                    m.last_order_date,
                    m.first_order_date,
                    COALESCE(m.days_since_last_order, 0) as days_since_last_order
                FROM analytics_v2.mv_customer_summary m
                LEFT JOIN analytics_v2.dim_customer d ON d.customer_id = m.customer_id
                WHERE m.client_id = :client_id
                ORDER BY m.lifetime_value DESC
            """)
            result = self.db_session.execute(query, {"client_id": client_id})
            rows = result.fetchall()

            return [
                {
                    "customer_id": str(row[0]) if row[0] else None,
                    "name": row[1],
                    "cpf_cnpj": row[2],
                    "estado": row[3],
                    "total_orders": int(row[4] or 0),
                    "lifetime_value": float(row[5] or 0),
                    "avg_order_value": float(row[6] or 0),
                    "total_quantity": float(row[7] or 0),
                    "last_order_date": str(row[8]) if row[8] else None,
                    "first_order_date": str(row[9]) if row[9] else None,
                    "days_since_last_order": int(row[10] or 0),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ Failed to read mv_customer_summary: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_mv_product_summary(self, client_id: str) -> list[dict]:
        """
        Read from mv_product_summary materialized view.
        Fast pre-computed product aggregations for dashboard.

        Returns: List of product summaries with:
        - product_id, product_name
        - times_sold, total_quantity_sold, total_revenue
        - avg_order_value, avg_price, min_price, max_price
        - last_sold_date, unique_customers
        """
        try:
            query = text("""
                SELECT
                    product_id,
                    product_name,
                    COALESCE(times_sold, 0) as times_sold,
                    COALESCE(total_quantity_sold, 0) as total_quantity_sold,
                    COALESCE(total_revenue, 0) as total_revenue,
                    COALESCE(avg_order_value, 0) as avg_order_value,
                    COALESCE(avg_price, 0) as avg_price,
                    COALESCE(min_price, 0) as min_price,
                    COALESCE(max_price, 0) as max_price,
                    last_sold_date,
                    COALESCE(unique_customers, 0) as unique_customers
                FROM analytics_v2.mv_product_summary
                WHERE client_id = :client_id
                ORDER BY total_revenue DESC
            """)
            result = self.db_session.execute(query, {"client_id": client_id})
            rows = result.fetchall()

            return [
                {
                    "product_id": str(row[0]) if row[0] else None,
                    "product_name": row[1],
                    "times_sold": int(row[2] or 0),
                    "total_quantity_sold": float(row[3] or 0),
                    "total_revenue": float(row[4] or 0),
                    "avg_order_value": float(row[5] or 0),
                    "avg_price": float(row[6] or 0),
                    "min_price": float(row[7] or 0),
                    "max_price": float(row[8] or 0),
                    "last_sold_date": str(row[9]) if row[9] else None,
                    "unique_customers": int(row[10] or 0),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ Failed to read mv_product_summary: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_mv_monthly_sales_trend(self, client_id: str) -> list[dict]:
        """
        Read from mv_monthly_sales_trend materialized view.
        Fast pre-computed monthly sales data for time-series charts.

        Returns: List of monthly data with:
        - month (YYYY-MM-DD format)
        - orders_that_month, unique_customers_that_month
        - revenue_that_month, avg_order_value_that_month
        """
        try:
            query = text("""
                SELECT
                    TO_CHAR(month, 'YYYY-MM') as month,
                    COALESCE(orders_that_month, 0) as orders_that_month,
                    COALESCE(unique_customers_that_month, 0) as unique_customers_that_month,
                    COALESCE(revenue_that_month, 0) as revenue_that_month,
                    COALESCE(avg_order_value_that_month, 0) as avg_order_value_that_month
                FROM analytics_v2.mv_monthly_sales_trend
                WHERE client_id = :client_id
                ORDER BY month ASC
            """)
            result = self.db_session.execute(query, {"client_id": client_id})
            rows = result.fetchall()

            return [
                {
                    "month": row[0],
                    "name": row[0],  # For chart compatibility (name is the x-axis label)
                    "orders": int(row[1] or 0),
                    "unique_customers": int(row[2] or 0),
                    "revenue": float(row[3] or 0),
                    "total": float(row[3] or 0),  # For chart compatibility
                    "avg_order_value": float(row[4] or 0),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ Failed to read mv_monthly_sales_trend: {e}", exc_info=True)
            self.db_session.rollback()
            return []

    def get_mv_dashboard_summary(self, client_id: str) -> dict:
        """
        Get dashboard summary metrics from materialized views.
        Combines all MV data into a single response for the home dashboard.
        """
        try:
            # Get counts from MVs
            customer_summary = self.get_mv_customer_summary(client_id)
            product_summary = self.get_mv_product_summary(client_id)
            monthly_trend = self.get_mv_monthly_sales_trend(client_id)

            total_revenue = sum(c.get("lifetime_value", 0) for c in customer_summary)
            total_orders = sum(c.get("total_orders", 0) for c in customer_summary)

            return {
                "total_customers": len(customer_summary),
                "total_products": len(product_summary),
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "avg_order_value": total_revenue / total_orders if total_orders > 0 else 0,
                "monthly_trend": monthly_trend,
                "top_customers": customer_summary[:10],
                "top_products": product_summary[:10],
            }
        except Exception as e:
            logger.error(f"❌ Failed to get MV dashboard summary: {e}", exc_info=True)
            return {
                "total_customers": 0,
                "total_products": 0,
                "total_orders": 0,
                "total_revenue": 0,
                "avg_order_value": 0,
                "monthly_trend": [],
                "top_customers": [],
                "top_products": [],
            }

