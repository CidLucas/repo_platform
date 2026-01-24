# src/analytics_api/services/metric_service.py
import logging

import numpy as np
import pandas as pd
from sqlalchemy import text
from analytics_api.data_access.postgres_repository import PostgresRepository
from analytics_api.services.data_quality_logger import DataQualityLogger
from analytics_api.schemas.metrics import (
    ChartData,
    ChartDataPoint,
    RankingItem,
    CadastralData,
    HomeScorecards,
    HomeMetricsResponse,
    FornecedoresOverviewResponse,
    ClientesOverviewResponse,
    ProdutosOverviewResponse,
    PedidosOverviewResponse,
    PedidoItem,
    FornecedorDetailResponse,
    ClienteDetailResponse,
    ProdutoDetailResponse,
    PedidoDetailResponse,
    PedidoItemDetalhe,
)

logger = logging.getLogger(__name__)

class MetricService:
    """
    Serviço Silver -> Gold (Refatorado v2)

    Implementa os requisitos de métricas avançadas (Cohorts, Preço Médio)
    e serve os Níveis 1, 2 e 3 de forma agnóstica.
    """

    def __init__(self, repository: PostgresRepository, client_id: str):
        self.repository = repository
        self.client_id = client_id
        self.today = pd.Timestamp.now(tz='UTC')

        logger.info(f"🚀 [MetricService] Initializing for client: {client_id}")

        # Load silver data
        self.df = self.repository.get_silver_dataframe(client_id)
        logger.info(f"📊 Silver dataframe loaded: {len(self.df) if self.df is not None else 0} rows, {len(self.df.columns) if self.df is not None else 0} columns")

        if self.df is None or self.df.empty:
            logger.warning(f"No silver data found for client_id: {self.client_id} - initializing empty service")
            # Initialize empty aggregated dataframes
            empty_cols = ['nome', 'receita_total', 'quantidade_total', 'num_pedidos_unicos',
                         'primeira_venda', 'ultima_venda', 'ticket_medio', 'qtd_media_por_pedido',
                         'frequencia_pedidos_mes', 'recencia_dias',
                         'valor_unitario_medio', 'cluster_score', 'cluster_tier']
            self.df = pd.DataFrame(columns=['order_id', 'data_transacao', 'valor_total_emitter',
                                            'quantidade', 'valor_unitario', 'receiver_nome',
                                            'emitter_nome', 'raw_product_description'])
            self.df_clientes_agg = pd.DataFrame(columns=empty_cols)
            self.df_fornecedores_agg = pd.DataFrame(columns=empty_cols)
            self.df_produtos_agg = pd.DataFrame(columns=empty_cols)
            return

        # --- Pré-processamento Crítico ---
        logger.debug(f"🔧 Starting preprocessing...")

        # Convert data_transacao to datetime, handling errors gracefully
        if 'data_transacao' in self.df.columns:
            try:
                self.df['data_transacao'] = pd.to_datetime(self.df['data_transacao'], utc=True, errors='coerce')
                # Log rows with null data_transacao (parsing failures)
                null_count = self.df['data_transacao'].isna().sum()
                if null_count > 0:
                    logger.warning(f"Failed to parse {null_count} data_transacao values; set to NaT")
            except Exception as e:
                logger.warning(f"Failed to convert data_transacao to datetime: {e}; using NaT")
                self.df['data_transacao'] = pd.NaT

        # Convert numeric columns, coercing errors to NaN
        if 'valor_total_emitter' in self.df.columns:
            self.df['valor_total_emitter'] = pd.to_numeric(self.df['valor_total_emitter'], errors='coerce')
        if 'quantidade' in self.df.columns:
            self.df['quantidade'] = pd.to_numeric(self.df['quantidade'], errors='coerce')
        if 'valor_unitario' in self.df.columns:
            self.df['valor_unitario'] = pd.to_numeric(self.df['valor_unitario'], errors='coerce')

        logger.debug(f"✓ Preprocessing completed")

        # Log which canonical columns we have
        canonical_expected = ['order_id', 'data_transacao', 'quantidade', 'valor_unitario',
                             'raw_product_description', 'receiver_nome', 'emitter_nome', 'valor_total_emitter']
        available_cols = list(self.df.columns)
        found_canonical = [col for col in canonical_expected if col in available_cols]
        missing_canonical = [col for col in canonical_expected if col not in available_cols]

        logger.info(f"📊 Canonical columns found: {found_canonical}")
        if missing_canonical:
            logger.warning(f"⚠️  Missing canonical columns: {missing_canonical}")
            logger.info(f"Available raw columns (first 20): {available_cols[:20]}")

        # Log silver input data quality at DEBUG level
        if logger.isEnabledFor(logging.DEBUG):
            DataQualityLogger.log_dataframe_describe(self.df, "Silver Input", "raw data")

        # Only compute ano_mes/ano_semana if data_transacao exists and has non-null values
        if 'data_transacao' in self.df.columns and not self.df['data_transacao'].isna().all():
            # Remove timezone before converting to period to avoid warnings
            dt_no_tz = self.df['data_transacao'].dt.tz_localize(None)
            self.df['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
            self.df['ano_semana'] = dt_no_tz.dt.to_period('W').astype(str)
            logger.info(f"✓ Date columns processed successfully")
        else:
            logger.warning(f"⚠️  data_transacao column not usable, skipping time-based features")
            self.df['ano_mes'] = ''
            self.df['ano_semana'] = ''

        # --- PRÉ-CÁLCULO DE COHORTS (Q2) ---
        # Pré-calculamos os tiers de *Clientes* e *Fornecedores*
        # para que possam ser usados em todos os módulos.
        logger.info(f"🔄 Computing aggregations...")

        self.df_clientes_agg = self._get_aggregated_metrics_by_dimension(self.df, 'receiver_nome')
        logger.info(f"  ✓ Customers aggregated: {len(self.df_clientes_agg)} records")

        self.df_fornecedores_agg = self._get_aggregated_metrics_by_dimension(self.df, 'emitter_nome')
        logger.info(f"  ✓ Suppliers aggregated: {len(self.df_fornecedores_agg)} records")

        # Products aggregation (use full metrics like customers/suppliers)
        self.df_produtos_agg = self._get_aggregated_metrics_by_dimension(self.df, 'raw_product_description')
        logger.info(f"  ✓ Products aggregated: {len(self.df_produtos_agg)} records")

        # Customer-Product aggregation (for mix_de_produtos in ClienteDetailsModal)
        self.df_customer_products_agg = self._get_customer_product_aggregation()
        logger.info(f"  ✓ Customer-Products aggregated: {len(self.df_customer_products_agg)} records")

        # --- PERSIST TO ANALYTICS_V2 TABLES ---
        # Write computed aggregations to analytics_v2 star schema for frontend queries
        logger.info(f"💾 Persisting aggregations to analytics_v2...")
        self._persist_to_analytics_v2()

        logger.info(f"✅ [MetricService] Initialization complete")


    # ---
    # HELPER AGREGADOR (ATUALIZADO PARA Q1 e Q2)
    # ---

    def _get_aggregated_metrics_by_dimension(self, df: pd.DataFrame, dimension_col: str) -> pd.DataFrame:
        """
        O CÉREBRO agnóstico de Nível 2 e 3. (Atualizado v2)
        Handles missing columns and NaN values gracefully.
        """
        if df.empty or dimension_col not in df.columns:
            cols = ['nome', 'receita_total', 'quantidade_total', 'num_pedidos_unicos',
                    'primeira_venda', 'ultima_venda', 'period_start', 'period_end',
                    'ticket_medio', 'qtd_media_por_pedido',
                    'frequencia_pedidos_mes', 'recencia_dias',
                    'valor_unitario_medio', # (Q1)
                    'score_r', 'score_f', 'score_m',
                    'cluster_score', 'cluster_tier'] # (Q2)
            return pd.DataFrame(columns=cols)

        # 1. Agregação Primária - only include columns that exist
        agg_ops = {}
        if 'valor_total_emitter' in df.columns:
            agg_ops['receita_total'] = ('valor_total_emitter', 'sum')
        if 'quantidade' in df.columns:
            agg_ops['quantidade_total'] = ('quantidade', 'sum')
        if 'order_id' in df.columns:
            agg_ops['num_pedidos_unicos'] = ('order_id', 'nunique')
        if 'data_transacao' in df.columns:
            agg_ops['primeira_venda'] = ('data_transacao', 'min')
            agg_ops['ultima_venda'] = ('data_transacao', 'max')
        if 'valor_unitario' in df.columns:
            agg_ops['valor_unitario_medio'] = ('valor_unitario', 'mean')

        # Preserve CNPJ/CPF fields using 'first' aggregation (they should be the same for each name)
        if dimension_col == 'emitter_nome' and 'emitter_cnpj' in df.columns:
            agg_ops['emitter_cnpj'] = ('emitter_cnpj', 'first')
        if dimension_col == 'receiver_nome' and 'receiver_cpf_cnpj' in df.columns:
            agg_ops['receiver_cpf_cnpj'] = ('receiver_cpf_cnpj', 'first')
            # Preserve contact and address fields for customers
            if 'receiver_telefone' in df.columns:
                agg_ops['receiver_telefone'] = ('receiver_telefone', 'first')
            if 'receiver_rua' in df.columns:
                agg_ops['receiver_rua'] = ('receiver_rua', 'first')
            if 'receiver_numero' in df.columns:
                agg_ops['receiver_numero'] = ('receiver_numero', 'first')
            if 'receiver_bairro' in df.columns:
                agg_ops['receiver_bairro'] = ('receiver_bairro', 'first')
            if 'receiver_cidade' in df.columns:
                agg_ops['receiver_cidade'] = ('receiver_cidade', 'first')
            if 'receiver_uf' in df.columns:
                agg_ops['receiver_uf'] = ('receiver_uf', 'first')
            elif 'receiverstateuf' in df.columns:
                agg_ops['receiverstateuf'] = ('receiverstateuf', 'first')
            if 'receiver_cep' in df.columns:
                agg_ops['receiver_cep'] = ('receiver_cep', 'first')

        if not agg_ops:
            logger.warning(f"No aggregatable columns found for {dimension_col}")
            return pd.DataFrame(columns=['nome', 'receita_total', 'quantidade_total', 'num_pedidos_unicos',
                                         'primeira_venda', 'ultima_venda', 'period_start', 'period_end',
                                         'ticket_medio', 'qtd_media_por_pedido',
                                         'frequencia_pedidos_mes', 'recencia_dias',
                                         'valor_unitario_medio', 'score_r', 'score_f', 'score_m',
                                         'cluster_score', 'cluster_tier'])

        agg_df = df.groupby(dimension_col).agg(**agg_ops).reset_index()
        logger.debug(f"  [Groupby] {dimension_col}: {len(agg_df)} groups")

        # 2. Métricas Derivadas (with defensive checks for missing columns)
        # Handle missing base columns - fill with 0 if they don't exist
        if 'receita_total' not in agg_df.columns:
            logger.warning(f"⚠️  receita_total not available for {dimension_col}, setting to 0")
            agg_df['receita_total'] = 0
        if 'quantidade_total' not in agg_df.columns:
            logger.warning(f"⚠️  quantidade_total not available for {dimension_col}, setting to 0")
            agg_df['quantidade_total'] = 0
        if 'valor_unitario_medio' not in agg_df.columns:
            logger.warning(f"⚠️  valor_unitario_medio not available for {dimension_col}, setting to 0")
            agg_df['valor_unitario_medio'] = 0

        # Handle missing num_pedidos_unicos (if order_id wasn't available)
        if 'num_pedidos_unicos' not in agg_df.columns:
            logger.warning(f"⚠️  num_pedidos_unicos not available for {dimension_col}, assuming 1 order per entity")
            agg_df['num_pedidos_unicos'] = 1

        agg_df['ticket_medio'] = agg_df['receita_total'] / agg_df['num_pedidos_unicos']
        agg_df['qtd_media_por_pedido'] = agg_df['quantidade_total'] / agg_df['num_pedidos_unicos']

        # Handle missing date columns
        if 'primeira_venda' in agg_df.columns and 'ultima_venda' in agg_df.columns:
            # Add period start/end columns
            agg_df['period_start'] = agg_df['primeira_venda']
            agg_df['period_end'] = agg_df['ultima_venda']

            # Calculate activity period
            dias_ativo = (agg_df['ultima_venda'] - agg_df['primeira_venda']).dt.days
            meses_ativo = (dias_ativo / 30.44).clip(lower=1)
            agg_df['frequencia_pedidos_mes'] = agg_df['num_pedidos_unicos'] / meses_ativo

            # FIXED: recencia_dias should be average days BETWEEN transactions, not days since last purchase
            # If only 1 order, return 0. If multiple orders, calculate average interval between consecutive orders.
            def calculate_avg_days_between_orders(entity_name):
                entity_df = df[df[dimension_col] == entity_name].sort_values('data_transacao')
                if len(entity_df) <= 1:
                    # Only one transaction - return 0 (no interval to calculate)
                    return 0
                # Calculate intervals between consecutive transactions
                intervals = entity_df['data_transacao'].diff().dt.days.dropna()
                return intervals.mean() if len(intervals) > 0 else 0

            # Apply before renaming dimension_col to 'nome'
            # ⚠️  WARNING: This apply() is O(n²) - iterates rows and filters df for each
            agg_df['recencia_dias'] = agg_df[dimension_col].apply(calculate_avg_days_between_orders)
        else:
            logger.warning(f"⚠️  Date columns missing, setting time-based metrics to 0")
            agg_df['period_start'] = None
            agg_df['period_end'] = None
            agg_df['frequencia_pedidos_mes'] = 0
            agg_df['recencia_dias'] = 0

        # 3. Cluster Vizu (Score Simples) - with safe division
        max_recencia = agg_df['recencia_dias'].max() if agg_df['recencia_dias'].max() > 0 else 1
        max_frequencia = agg_df['frequencia_pedidos_mes'].max() if agg_df['frequencia_pedidos_mes'].max() > 0 else 1
        max_receita = agg_df['receita_total'].max() if agg_df['receita_total'].max() > 0 else 1

        agg_df['score_r'] = (1 - (agg_df['recencia_dias'] / max_recencia)) * 100
        agg_df['score_f'] = (agg_df['frequencia_pedidos_mes'] / max_frequencia) * 100
        agg_df['score_m'] = (agg_df['receita_total'] / max_receita) * 100
        agg_df['cluster_score'] = (agg_df['score_r'] * 0.2) + (agg_df['score_f'] * 0.4) + (agg_df['score_m'] * 0.4)

        # ATUALIZADO (Q2): Criar Tiers (Segmentos)
        # Usamos qcut (quantil) para dividir em 4 grupos (A, B, C, D)
        if agg_df['cluster_score'].nunique() > 1:
            try:
                agg_df['cluster_tier'] = pd.qcut(agg_df['cluster_score'], 4, labels=["D", "C", "B", "A"])
            except ValueError:
                # Fallback se não houver dados suficientes para 4 quantis
                agg_df['cluster_tier'] = "C"
        else:
            agg_df['cluster_tier'] = "C" # Tier único

        # --- ADICIONE ESTA LINHA ---
        # Converte a coluna categórica para string antes do fillna
        agg_df['cluster_tier'] = agg_df['cluster_tier'].astype(str)
        # --- FIM DA ADIÇÃO ---

        agg_df.rename(columns={dimension_col: 'nome'}, inplace=True)
        agg_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        agg_df.fillna(0, inplace=True)

        return agg_df

    def _get_customer_product_aggregation(self) -> pd.DataFrame:
        """
        Aggregate product metrics per customer (customer_cpf_cnpj + product_name).
        This enables fast lookup of "what products did this customer buy" from gold tables.
        Used by ClienteDetailsModal to show mix_de_produtos_por_receita.
        """
        required_cols = ['receiver_cpf_cnpj', 'raw_product_description']
        if self.df.empty or not all(col in self.df.columns for col in required_cols):
            logger.warning("Cannot compute customer-product aggregation: missing required columns")
            return pd.DataFrame(columns=[
                'customer_cpf_cnpj', 'customer_name', 'product_name',
                'receita_total', 'quantidade_total', 'num_pedidos',
                'valor_unitario_medio', 'primeira_compra', 'ultima_compra'
            ])

        # Filter out rows with missing customer identifier
        df_valid = self.df[self.df['receiver_cpf_cnpj'].notna()].copy()
        if df_valid.empty:
            logger.warning("No valid customer CPF/CNPJ data for customer-product aggregation")
            return pd.DataFrame()

        # Build aggregation operations
        agg_ops = {
            'receita_total': ('valor_total_emitter', 'sum') if 'valor_total_emitter' in df_valid.columns else ('receiver_cpf_cnpj', 'count'),
            'quantidade_total': ('quantidade', 'sum') if 'quantidade' in df_valid.columns else ('receiver_cpf_cnpj', 'count'),
        }

        if 'order_id' in df_valid.columns:
            agg_ops['num_pedidos'] = ('order_id', 'nunique')
        if 'valor_unitario' in df_valid.columns:
            agg_ops['valor_unitario_medio'] = ('valor_unitario', 'mean')
        if 'data_transacao' in df_valid.columns:
            agg_ops['primeira_compra'] = ('data_transacao', 'min')
            agg_ops['ultima_compra'] = ('data_transacao', 'max')
        if 'receiver_nome' in df_valid.columns:
            agg_ops['customer_name'] = ('receiver_nome', 'first')

        # Group by customer + product
        agg_df = df_valid.groupby(['receiver_cpf_cnpj', 'raw_product_description']).agg(**agg_ops).reset_index()

        # Rename columns to match gold table schema
        agg_df.rename(columns={
            'receiver_cpf_cnpj': 'customer_cpf_cnpj',
            'raw_product_description': 'product_name',
        }, inplace=True)

        # Fill missing columns with defaults
        if 'num_pedidos' not in agg_df.columns:
            agg_df['num_pedidos'] = 1
        if 'valor_unitario_medio' not in agg_df.columns:
            agg_df['valor_unitario_medio'] = 0
        if 'primeira_compra' not in agg_df.columns:
            agg_df['primeira_compra'] = None
        if 'ultima_compra' not in agg_df.columns:
            agg_df['ultima_compra'] = None
        if 'customer_name' not in agg_df.columns:
            agg_df['customer_name'] = None

        # Clean up NaN/inf values
        agg_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        agg_df.fillna({'receita_total': 0, 'quantidade_total': 0, 'num_pedidos': 0, 'valor_unitario_medio': 0}, inplace=True)

        return agg_df

    # =====================================================================
    # Write methods: Persist computed metrics to gold tables
    # =====================================================================

    def _persist_to_analytics_v2(self) -> None:
        """
        Persist computed aggregations to analytics_v2 star schema.
        Called after all aggregations are computed to make data available for frontend/queries.

        Tables written:
        - analytics_v2.dim_customer (from df_clientes_agg)
        - analytics_v2.dim_supplier (from df_fornecedores_agg)
        - analytics_v2.dim_product (from df_produtos_agg)
        - analytics_v2.fact_sales (transaction-level from df)
        - analytics_v2.customer_products (customer-product relationships)
        """
        import time

        if self.df.empty:
            logger.debug("No data available; skipping persistence")
            return

        try:
            # Write customers dimension
            if not self.df_clientes_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_clientes_agg)} customers to analytics_v2.dim_customer...")
                customers_data = self.df_clientes_agg.to_dict('records')
                try:
                    self.repository.write_star_customers(self.client_id, customers_data)
                    logger.info(f"    ✓ Persisted {len(customers_data)} customers")
                except Exception as e:
                    logger.error(f"    ✗ Failed: {e}", exc_info=True)
                    raise

                # After ensuring dim_customer rows exist, compute and populate derived aggregates
                try:
                    self._populate_dim_customer_aggregates()
                except Exception as e:
                    logger.warning(f"Failed to populate dim_customer aggregates: {e}")

            # Write suppliers dimension
            if not self.df_fornecedores_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_fornecedores_agg)} suppliers to analytics_v2.dim_supplier...")
                suppliers_data = self.df_fornecedores_agg.to_dict('records')
                try:
                    self.repository.write_star_suppliers(self.client_id, suppliers_data)
                    logger.info(f"    ✓ Persisted {len(suppliers_data)} suppliers")
                except Exception as e:
                    logger.error(f"    ✗ Failed: {e}", exc_info=True)
                    raise
                # After ensuring dim_supplier rows exist, compute and populate derived aggregates
                try:
                    self._populate_dim_supplier_aggregates()
                except Exception as e:
                    logger.warning(f"Failed to populate dim_supplier aggregates: {e}")

            # Write products dimension
            if not self.df_produtos_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_produtos_agg)} products to analytics_v2.dim_product...")
                products_data = self.df_produtos_agg.to_dict('records')
                try:
                    self.repository.write_star_products(self.client_id, products_data)
                    logger.info(f"    ✓ Persisted {len(products_data)} products")
                except Exception as e:
                    logger.error(f"    ✗ Failed: {e}", exc_info=True)
                    raise

                # After ensuring dim_product rows exist, compute and populate derived aggregates
                try:
                    self._populate_dim_product_aggregates()
                except Exception as e:
                    logger.warning(f"Failed to populate dim_product aggregates: {e}")

            # Write fact_sales (transaction-level data)
            if not self.df.empty:
                logger.info(f"  ➜ Writing transaction-level data to analytics_v2.fact_sales...")
                required_cols = ['order_id', 'data_transacao', 'quantidade', 'valor_unitario', 'valor_total_emitter',
                               'receiver_cpf_cnpj', 'emitter_cnpj', 'raw_product_description']
                available_cols = [col for col in required_cols if col in self.df.columns]

                if available_cols:
                    transactions_data = self.df[available_cols].copy().to_dict('records')
                    try:
                        sales_count = self.repository.write_fact_sales(self.client_id, transactions_data)
                        logger.info(f"    ✓ Persisted {sales_count} transactions")
                    except Exception as e:
                        logger.error(f"    ✗ Failed: {e}", exc_info=True)
                        raise
                else:
                    logger.warning(f"    ⚠️  No transaction columns available for fact_sales")

            # Write customer-product relationships
            if not self.df_customer_products_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_customer_products_agg)} customer-product relationships...")
                customer_products_data = self.df_customer_products_agg.to_dict('records')
                try:
                    self.repository.write_star_customer_products(self.client_id, customer_products_data)
                    logger.info(f"    ✓ Persisted {len(customer_products_data)} relationships")
                except Exception as e:
                    logger.error(f"    ✗ Failed: {e}", exc_info=True)
                    raise

            logger.info(f"✅ All analytics_v2 aggregations persisted successfully")

        except Exception as e:
            logger.error(f"❌ Failed to persist to analytics_v2: {e}", exc_info=True)
            raise

    def _populate_dim_product_aggregates(self) -> None:
        """Compute and populate product aggregates (totals, recency/frequency, cluster score/tier).

        Runs idempotent SQL updates scoped to `self.client_id`. Safe to call repeatedly.
        """
        conn = self.repository.db_session
        client = self.client_id

        try:
            logger.info("  ➜ Populating dim_product aggregates from fact_sales (this may take a while)...")
            with conn.begin():
                # 1) totals, avg price, avg quantity per order
                q1 = text("""
                WITH prod_stats AS (
                    SELECT
                        p.product_id,
                        COALESCE(SUM(f.quantidade),0)::numeric AS total_quantity,
                        COALESCE(SUM(f.valor_total),0)::numeric AS total_revenue,
                        COUNT(DISTINCT f.order_id)::int AS number_of_orders,
                        CASE WHEN COUNT(DISTINCT f.order_id) > 0 THEN COALESCE(SUM(f.quantidade)::numeric / NULLIF(COUNT(DISTINCT f.order_id),0),0) ELSE 0 END AS avg_quantity_per_order,
                        CASE WHEN COUNT(f.*) > 0 THEN COALESCE(AVG(f.valor_total),0) ELSE 0 END AS avg_price
                    FROM analytics_v2.fact_sales f
                    JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                    WHERE p.client_id = :client_id
                    GROUP BY p.product_id
                )
                UPDATE analytics_v2.dim_product dp
                SET
                    total_quantity_sold = s.total_quantity,
                    total_revenue = s.total_revenue,
                    number_of_orders = s.number_of_orders,
                    avg_quantity_per_order = s.avg_quantity_per_order,
                    avg_price = s.avg_price,
                    updated_at = now()
                FROM prod_stats s
                WHERE dp.product_id = s.product_id AND dp.client_id = :client_id
                """)
                conn.execute(q1, {'client_id': client})

                # 2) frequency_per_month, recency_days, last_sale_date
                q2 = text("""
                WITH per_product_dates AS (
                    SELECT
                        p.product_id,
                        MIN(f.data_transacao)::date AS first_sale,
                        MAX(f.data_transacao)::date AS last_sale,
                        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active,
                        COUNT(DISTINCT f.order_id) AS orders
                    FROM analytics_v2.fact_sales f
                    JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                    WHERE p.client_id = :client_id
                    GROUP BY p.product_id
                ),
                                recency AS (
                                    SELECT product_id, ROUND(AVG(diff_days))::int AS avg_recency_days FROM (
                                        SELECT
                                            f.product_id,
                                            EXTRACT(epoch FROM (f.data_transacao - lag(f.data_transacao) OVER (PARTITION BY f.product_id ORDER BY f.data_transacao)))/86400 AS diff_days
                                        FROM analytics_v2.fact_sales f
                                        JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                                        WHERE p.client_id = :client_id
                                    ) sub
                                    WHERE diff_days IS NOT NULL
                                    GROUP BY product_id
                                )
                UPDATE analytics_v2.dim_product dp
                SET
                    frequency_per_month = COALESCE(pd.orders::numeric / NULLIF(pd.months_active,0), 0),
                    recency_days = COALESCE(r.avg_recency_days,0),
                    last_sale_date = pd.last_sale,
                    updated_at = now()
                FROM per_product_dates pd
                LEFT JOIN recency r ON r.product_id = pd.product_id
                WHERE dp.product_id = pd.product_id AND dp.client_id = :client_id
                """)
                conn.execute(q2, {'client_id': client})

                # 3) cluster_score
                q3 = text("""
                WITH maxima AS (
                    SELECT
                        GREATEST(MAX(COALESCE(recency_days,0)),1) AS max_recency,
                        GREATEST(MAX(COALESCE(frequency_per_month,0)),1) AS max_freq,
                        GREATEST(MAX(COALESCE(total_revenue,0)),1) AS max_revenue
                    FROM analytics_v2.dim_product
                    WHERE client_id = :client_id
                ),
                scores AS (
                    SELECT
                        dp.product_id,
                        (
                            (1 - (COALESCE(dp.recency_days,0)::numeric / m.max_recency)) * 0.2
                            + (COALESCE(dp.frequency_per_month,0) / m.max_freq) * 0.4
                            + (COALESCE(dp.total_revenue,0) / m.max_revenue) * 0.4
                        ) * 100 AS cluster_score
                    FROM analytics_v2.dim_product dp
                    CROSS JOIN maxima m
                    WHERE dp.client_id = :client_id
                )
                UPDATE analytics_v2.dim_product dp
                SET cluster_score = s.cluster_score,
                        updated_at = now()
                FROM scores s
                WHERE dp.product_id = s.product_id AND dp.client_id = :client_id
                """)
                conn.execute(q3, {'client_id': client})

                # 4) cluster_tier quartiles
                q4 = text("""
                WITH ranked AS (
                    SELECT
                        product_id,
                        ntile(4) OVER (ORDER BY cluster_score) AS quartile
                    FROM analytics_v2.dim_product
                    WHERE client_id = :client_id
                )
                UPDATE analytics_v2.dim_product dp
                SET cluster_tier = CASE r.quartile WHEN 4 THEN 'A' WHEN 3 THEN 'B' WHEN 2 THEN 'C' ELSE 'D' END,
                        updated_at = now()
                FROM ranked r
                WHERE dp.product_id = r.product_id AND dp.client_id = :client_id
                """)
                conn.execute(q4, {'client_id': client})

            logger.info("    ✓ dim_product aggregates populated")
        except Exception as e:
            logger.error(f"    ✗ Error populating dim_product aggregates: {e}", exc_info=True)
            raise

    def _populate_dim_customer_aggregates(self) -> None:
        """Compute and populate customer aggregates (orders_last_30_days, frequency_per_month, recency_days).

        Runs idempotent SQL updates scoped to `self.client_id`. Safe to call repeatedly.
        """
        conn = self.repository.db_session
        client = self.client_id

        try:
            logger.info("  ➜ Populating dim_customer aggregates from fact_sales...")
            with conn.begin():
                # 1) basic totals and last_30_days
                q1 = text("""
                WITH cust_stats AS (
                    SELECT
                        c.customer_id,
                        COUNT(DISTINCT f.order_id)::int AS total_orders,
                        COALESCE(SUM(f.valor_total),0)::numeric AS total_revenue,
                        COALESCE(SUM(f.quantidade),0)::numeric AS total_quantity,
                        COUNT(DISTINCT CASE WHEN f.data_transacao >= now() - interval '30 days' THEN f.order_id END)::int AS orders_last_30_days,
                        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active
                    FROM analytics_v2.fact_sales f
                    JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                    WHERE c.client_id = :client_id
                    GROUP BY c.customer_id
                )
                UPDATE analytics_v2.dim_customer dc
                SET
                    total_orders = s.total_orders,
                    total_revenue = s.total_revenue,
                    total_quantity = s.total_quantity,
                    orders_last_30_days = s.orders_last_30_days,
                    updated_at = now()
                FROM cust_stats s
                WHERE dc.customer_id = s.customer_id AND dc.client_id = :client_id
                """)
                conn.execute(q1, {'client_id': client})

                # 2) frequency_per_month and recency_days (avg days between orders)
                q2 = text("""
                WITH per_customer AS (
                                    SELECT
                                        f.customer_id AS customer_id,
                                        COUNT(DISTINCT f.order_id) AS orders,
                                        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active
                                    FROM analytics_v2.fact_sales f
                                    JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                                    WHERE c.client_id = :client_id
                                    GROUP BY f.customer_id
                ),
                                recency AS (
                                    SELECT customer_id, ROUND(AVG(diff_days))::int AS avg_recency_days FROM (
                                        SELECT
                                            f.customer_id,
                                            EXTRACT(epoch FROM (f.data_transacao - lag(f.data_transacao) OVER (PARTITION BY f.customer_id ORDER BY f.data_transacao)))/86400 AS diff_days
                                        FROM analytics_v2.fact_sales f
                                        JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                                        WHERE c.client_id = :client_id
                                    ) sub
                                    WHERE diff_days IS NOT NULL
                                    GROUP BY customer_id
                                )
                UPDATE analytics_v2.dim_customer dc
                SET
                    frequency_per_month = COALESCE(pc.orders::numeric / NULLIF(pc.months_active,0), 0),
                    recency_days = COALESCE(r.avg_recency_days, 0),
                    updated_at = now()
                FROM per_customer pc
                LEFT JOIN recency r ON r.customer_id = pc.customer_id
                WHERE dc.customer_id = pc.customer_id AND dc.client_id = :client_id
                """)
                conn.execute(q2, {'client_id': client})

            logger.info("    ✓ dim_customer aggregates populated")
        except Exception as e:
            logger.error(f"    ✗ Error populating dim_customer aggregates: {e}", exc_info=True)
            raise

    def _populate_dim_supplier_aggregates(self) -> None:
        """Compute and populate supplier aggregates (orders_last_30_days, frequency_per_month, recency_days).

        Runs idempotent SQL updates scoped to `self.client_id`. Safe to call repeatedly.
        """
        conn = self.repository.db_session
        client = self.client_id

        try:
            logger.info("  ➜ Populating dim_supplier aggregates from fact_sales...")
            with conn.begin():
                # 1) basic totals and last_30_days
                q1 = text("""
                                WITH supp_stats AS (
                                    SELECT
                                        f.supplier_id AS supplier_id,
                                        COUNT(DISTINCT f.order_id)::int AS total_orders,
                                        COALESCE(SUM(f.valor_total),0)::numeric AS total_revenue,
                                        CASE WHEN COUNT(DISTINCT f.order_id) > 0 THEN COALESCE(SUM(f.quantidade)::numeric / NULLIF(COUNT(DISTINCT f.order_id),0),0) ELSE 0 END AS avg_products_per_order,
                                        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active,
                                        MIN(f.data_transacao)::date AS first_tx,
                                        MAX(f.data_transacao)::date AS last_tx,
                                        CASE WHEN COUNT(DISTINCT f.order_id) > 0 THEN COALESCE(SUM(f.valor_total)::numeric / NULLIF(COUNT(DISTINCT f.order_id),0),0) ELSE 0 END AS avg_order_value
                                    FROM analytics_v2.fact_sales f
                                    JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                                    WHERE s.client_id = :client_id
                                    GROUP BY f.supplier_id
                                )
                                UPDATE analytics_v2.dim_supplier ds
                                SET
                                    total_orders_received = ss.total_orders,
                                    total_revenue = ss.total_revenue,
                                    avg_order_value = ss.avg_order_value,
                                    total_products_supplied = ss.avg_products_per_order,
                                    first_transaction_date = ss.first_tx,
                                    last_transaction_date = ss.last_tx,
                                    updated_at = now()
                                FROM supp_stats ss
                                WHERE ds.supplier_id = ss.supplier_id AND ds.client_id = :client_id
                                """)
                conn.execute(q1, {'client_id': client})

                # 2) frequency_per_month and recency_days (avg days between orders)
                q2 = text("""
                WITH per_supplier AS (
                    SELECT
                                        f.supplier_id AS supplier_id,
                        COUNT(DISTINCT f.order_id) AS orders,
                        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active
                                    FROM analytics_v2.fact_sales f
                                    JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                                    WHERE s.client_id = :client_id
                                    GROUP BY f.supplier_id
                ),
                                recency AS (
                                    SELECT supplier_id, ROUND(AVG(diff_days))::int AS avg_recency_days FROM (
                                        SELECT
                                            f.supplier_id,
                                            EXTRACT(epoch FROM (f.data_transacao - lag(f.data_transacao) OVER (PARTITION BY f.supplier_id ORDER BY f.data_transacao)))/86400 AS diff_days
                                        FROM analytics_v2.fact_sales f
                                        JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                                        WHERE s.client_id = :client_id
                                    ) sub
                                    WHERE diff_days IS NOT NULL
                                    GROUP BY supplier_id
                                )
                UPDATE analytics_v2.dim_supplier ds
                SET
                                    frequency_per_month = COALESCE(ps.orders::numeric / NULLIF(ps.months_active,0), 0),
                                    recency_days = COALESCE(r.avg_recency_days, 0),
                    updated_at = now()
                FROM per_supplier ps
                LEFT JOIN recency r ON r.supplier_id = ps.supplier_id
                WHERE ds.supplier_id = ps.supplier_id AND ds.client_id = :client_id
                """)
                conn.execute(q2, {'client_id': client})

            logger.info("    ✓ dim_supplier aggregates populated")
        except Exception as e:
            logger.error(f"    ✗ Error populating dim_supplier aggregates: {e}", exc_info=True)
            raise

    def _calculate_orders_metrics(self) -> list[dict]:
        """
        Calculate order metrics for both all-time and monthly periods.

        Returns:
            List of dicts with metrics for each period:
            - 1 all-time aggregate
            - N monthly aggregates (one per month in the data)
        """
        metrics_list = []

        # Validate required columns
        if self.df.empty or 'order_id' not in self.df.columns:
            logger.warning("Cannot calculate orders metrics: missing order_id column")
            return metrics_list

        has_dates = 'data_transacao' in self.df.columns and not self.df['data_transacao'].isna().all()
        has_revenue = 'valor_total_emitter' in self.df.columns
        has_quantity = 'quantidade' in self.df.columns

        # --- ALL-TIME METRICS ---
        try:
            period_start = self.df['data_transacao'].min() if has_dates else None
            period_end = self.df['data_transacao'].max() if has_dates else None
            total_orders = int(self.df['order_id'].nunique())
            total_revenue = float(self.df['valor_total_emitter'].sum()) if has_revenue else 0.0
            quantidade_total = float(self.df['quantidade'].sum()) if has_quantity else 0.0

            # Calculate frequency and recency
            frequencia_pedidos_mes = 0.0
            recencia_dias = 0
            if has_dates and period_start and period_end:
                dias_ativo = (period_end - period_start).days
                meses_ativo = max((dias_ativo / 30.44), 1)  # At least 1 month
                frequencia_pedidos_mes = float(total_orders / meses_ativo)

                # Recency: average days between consecutive orders
                if total_orders > 1:
                    df_sorted = self.df.sort_values('data_transacao')
                    intervals = df_sorted['data_transacao'].diff().dt.days.dropna()
                    recencia_dias = int(intervals.mean()) if len(intervals) > 0 else 0

            all_time_metrics = {
                "period_type": "all_time",
                "period_start": period_start,
                "period_end": period_end,
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "avg_order_value": float(total_revenue / total_orders) if total_orders > 0 else 0.0,
                "quantidade_total": quantidade_total,
                "frequencia_pedidos_mes": frequencia_pedidos_mes,
                "recencia_dias": recencia_dias,
                "primeira_transacao": period_start,
                "ultima_transacao": period_end,
            }
            metrics_list.append(all_time_metrics)
            logger.info(f"    ✓ All-time metrics: {total_orders} orders, {total_revenue:.2f} revenue, {frequencia_pedidos_mes:.2f} freq/mo")

        except Exception as e:
            logger.error(f"Failed to calculate all-time order metrics: {e}", exc_info=True)

        # --- MONTHLY METRICS ---
        if has_dates and 'ano_mes' in self.df.columns:
            try:
                # Group by month
                for period, df_month in self.df.groupby('ano_mes'):
                    if df_month.empty:
                        continue

                    period_start_month = df_month['data_transacao'].min()
                    period_end_month = df_month['data_transacao'].max()
                    total_orders_month = int(df_month['order_id'].nunique())
                    total_revenue_month = float(df_month['valor_total_emitter'].sum()) if has_revenue else 0.0
                    quantidade_total_month = float(df_month['quantidade'].sum()) if has_quantity else 0.0

                    # For monthly metrics, frequency is orders per month (always in this month)
                    frequencia_pedidos_mes_month = float(total_orders_month)

                    # Recency: average days between orders within this month
                    recencia_dias_month = 0
                    if total_orders_month > 1:
                        df_sorted = df_month.sort_values('data_transacao')
                        intervals = df_sorted['data_transacao'].diff().dt.days.dropna()
                        recencia_dias_month = int(intervals.mean()) if len(intervals) > 0 else 0

                    monthly_metrics = {
                        "period_type": "monthly",
                        "period_start": period_start_month,
                        "period_end": period_end_month,
                        "total_orders": total_orders_month,
                        "total_revenue": total_revenue_month,
                        "avg_order_value": float(total_revenue_month / total_orders_month) if total_orders_month > 0 else 0.0,
                        "quantidade_total": quantidade_total_month,
                        "frequencia_pedidos_mes": frequencia_pedidos_mes_month,
                        "recencia_dias": recencia_dias_month,
                        "primeira_transacao": period_start_month,
                        "ultima_transacao": period_end_month,
                    }
                    metrics_list.append(monthly_metrics)

                logger.info(f"    ✓ Monthly metrics: {len(metrics_list) - 1} months calculated")

            except Exception as e:
                logger.error(f"Failed to calculate monthly order metrics: {e}", exc_info=True)

        return metrics_list

    def _calculate_total_regions(self) -> int:
        """
        Calculate total unique regions (states/UF) across both suppliers and customers.
        Returns the count of distinct regions present in the data.
        """
        unique_regions = set()

        # Check emitter (supplier) regions
        for col in ['emitterstateuf', 'emitter_estado', 'emitter_state']:
            if col in self.df.columns:
                regions = self.df[col].dropna().unique()
                unique_regions.update(regions)
                break

        # Check receiver (customer) regions
        for col in ['receiverstateuf', 'receiver_estado', 'receiver_state']:
            if col in self.df.columns:
                regions = self.df[col].dropna().unique()
                unique_regions.update(regions)
                break

        total = len(unique_regions)
        logger.info(f"  ✓ Calculated {total} unique regions")
        return total

    def _calculate_growth_percentage(self, current_count: int, previous_count: int) -> float | None:
        """
        Calculate period-over-period growth percentage.

        Args:
            current_count: Count in current period
            previous_count: Count in previous period

        Returns:
            Growth percentage (e.g., 15.5 for 15.5% growth) or None if no previous data
        """
        if previous_count == 0 or previous_count is None:
            return None

        growth = ((current_count - previous_count) / previous_count) * 100
        return round(growth, 2)

    def _calculate_time_series_growth(self, dimension_col: str, entity_name_col: str) -> float | None:
        """
        Calculate growth rate by comparing current month vs previous month unique entities.

        Args:
            dimension_col: Column name for time dimension (e.g., 'ano_mes')
            entity_name_col: Column name for entity to count (e.g., 'emitter_nome', 'receiver_nome')

        Returns:
            Growth percentage or None if insufficient data
        """
        if self.df.empty or dimension_col not in self.df.columns or entity_name_col not in self.df.columns:
            return None

        try:
            # Group by month and count unique entities (cumulative)
            df_time = self.df.dropna(subset=[dimension_col, entity_name_col])
            time_series = df_time.groupby(dimension_col)[entity_name_col].nunique().sort_index()

            if len(time_series) < 2:
                return None  # Need at least 2 periods for comparison

            # Get last two periods
            previous_count = time_series.iloc[-2]
            current_count = time_series.iloc[-1]

            return self._calculate_growth_percentage(int(current_count), int(previous_count))

        except Exception as e:
            logger.warning(f"Failed to calculate time series growth: {e}")
            return None

    def _write_v2_charts(self) -> None:
        """
        Write precomputed chart data (time series, regional, last orders) to v2 star schema.
        This eliminates the need to load full Silver dataframe on every module page view.
        """
        try:
            logger.info(f"📊 Computing and writing chart data to analytics_v2...")

            # 1. Time Series Charts
            self._write_time_series_charts()

            # 2. Regional Breakdown Charts
            self._write_regional_charts()

            # 3. Last Orders
            self._write_last_orders()

            logger.info(f"✅ All chart data written successfully")

        except Exception as e:
            logger.error(f"❌ Failed to write chart data: {e}", exc_info=True)

    def _write_time_series_charts(self) -> None:
        """Compute and write time-series aggregations (fornecedores_no_tempo, etc.)"""
        if self.df.empty or 'data_transacao' not in self.df.columns:
            logger.warning("No data_transacao available for time series")
            return

        try:
            # Collect ALL time series data first, then write in a single batch
            all_time_series_data = []

            # Fornecedores no tempo
            if 'emitter_nome' in self.df.columns:
                df_time = self.df.copy()
                # Remove timezone before converting to period to avoid warnings
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['emitter_nome'].nunique().reset_index()
                time_series.rename(columns={'emitter_nome': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'fornecedores_no_tempo',
                        'dimension': 'suppliers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),  # Convert to Python date
                        'total': int(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} fornecedores time series points")

            # Clientes no tempo (customers over time)
            if 'receiver_nome' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['receiver_nome'].nunique().reset_index()
                time_series.rename(columns={'receiver_nome': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'clientes_no_tempo',
                        'dimension': 'customers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': int(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} clientes time series points")

            # Produtos no tempo (products over time)
            if 'raw_product_description' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['raw_product_description'].nunique().reset_index()
                time_series.rename(columns={'raw_product_description': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'produtos_no_tempo',
                        'dimension': 'products',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': int(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} produtos time series points")

            # Pedidos no tempo (orders over time - count of orders, not unique entities)
            if 'order_id' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                # For orders, count unique order_ids per month
                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['order_id'].nunique().reset_index()
                time_series.rename(columns={'order_id': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'pedidos_no_tempo',
                        'dimension': 'orders',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': int(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} pedidos time series points")

            # --- NEW: Revenue, Ticket Medio, and Quantidade time series ---

            # Receita de Fornecedores no tempo (supplier revenue over time)
            if 'emitter_nome' in self.df.columns and 'valor_total_emitter' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['valor_total_emitter'].sum().reset_index()
                time_series.rename(columns={'valor_total_emitter': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'receita_fornecedores_no_tempo',
                        'dimension': 'suppliers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} receita fornecedores time series points")

            # Ticket Médio de Fornecedores no tempo
            if 'emitter_nome' in self.df.columns and 'valor_total_emitter' in self.df.columns and 'order_id' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                # Calculate ticket medio = total revenue / unique orders per month
                grouped = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date']).agg({
                    'valor_total_emitter': 'sum',
                    'order_id': 'nunique'
                }).reset_index()
                grouped['total'] = grouped['valor_total_emitter'] / grouped['order_id']

                chart_data = [
                    {
                        'chart_type': 'ticket_medio_fornecedores_no_tempo',
                        'dimension': 'suppliers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in grouped.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} ticket medio fornecedores time series points")

            # Quantidade de Fornecedores no tempo (volume in kg/ton)
            if 'emitter_nome' in self.df.columns and 'quantidade' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['quantidade'].sum().reset_index()
                time_series.rename(columns={'quantidade': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'quantidade_fornecedores_no_tempo',
                        'dimension': 'suppliers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} quantidade fornecedores time series points")

            # Receita de Clientes no tempo (customer revenue over time)
            if 'receiver_nome' in self.df.columns and 'valor_total_emitter' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['valor_total_emitter'].sum().reset_index()
                time_series.rename(columns={'valor_total_emitter': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'receita_clientes_no_tempo',
                        'dimension': 'customers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} receita clientes time series points")

            # Ticket Médio de Clientes no tempo
            if 'receiver_nome' in self.df.columns and 'valor_total_emitter' in self.df.columns and 'order_id' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                grouped = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date']).agg({
                    'valor_total_emitter': 'sum',
                    'order_id': 'nunique'
                }).reset_index()
                grouped['total'] = grouped['valor_total_emitter'] / grouped['order_id']

                chart_data = [
                    {
                        'chart_type': 'ticket_medio_clientes_no_tempo',
                        'dimension': 'customers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in grouped.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} ticket medio clientes time series points")

            # Quantidade de Clientes no tempo (volume purchased)
            if 'receiver_nome' in self.df.columns and 'quantidade' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['quantidade'].sum().reset_index()
                time_series.rename(columns={'quantidade': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'quantidade_clientes_no_tempo',
                        'dimension': 'customers',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} quantidade clientes time series points")

            # Receita de Produtos no tempo (product revenue over time)
            if 'raw_product_description' in self.df.columns and 'valor_total_emitter' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['valor_total_emitter'].sum().reset_index()
                time_series.rename(columns={'valor_total_emitter': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'receita_produtos_no_tempo',
                        'dimension': 'products',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} receita produtos time series points")

            # Quantidade de Produtos no tempo (volume sold)
            if 'raw_product_description' in self.df.columns and 'quantidade' in self.df.columns:
                df_time = self.df.copy()
                dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
                df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
                df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

                time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['quantidade'].sum().reset_index()
                time_series.rename(columns={'quantidade': 'total'}, inplace=True)

                chart_data = [
                    {
                        'chart_type': 'quantidade_produtos_no_tempo',
                        'dimension': 'products',
                        'period': row['ano_mes'],
                        'period_date': pd.Timestamp(row['period_date']).date(),
                        'total': float(row['total'])
                    }
                    for _, row in time_series.iterrows()
                ]
                all_time_series_data.extend(chart_data)
                logger.info(f"  ✓ Computed {len(chart_data)} quantidade produtos time series points")

            # Write all time series data to v2
            if all_time_series_data:
                try:
                    v2_count = self.repository.write_star_time_series(self.client_id, all_time_series_data)
                    logger.info(f"  ✓ Written {v2_count} time series points to analytics_v2")
                except Exception as e:
                    logger.error(f"  ✗ Failed to write v2 time_series: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to write time series charts: {e}", exc_info=True)

    def _write_regional_charts(self) -> None:
        """Compute and write regional breakdowns (fornecedores_por_regiao, etc.)"""
        if self.df.empty:
            logger.warning("No data available for regional charts")
            return

        try:
            # Fornecedores por região (state)
            if 'emitter_nome' in self.df.columns:
                state_col = None
                for col in ['emitterstateuf', 'emitter_estado', 'emitter_state']:
                    if col in self.df.columns:
                        state_col = col
                        break

                if state_col:
                    df_reg = self.df.groupby(state_col)['emitter_nome'].nunique().reset_index()
                    df_reg.rename(columns={state_col: 'region_name', 'emitter_nome': 'total'}, inplace=True)
                    total = df_reg['total'].sum() or 1
                    df_reg['percentual'] = (df_reg['total'] / total * 100).round(2)
                    df_reg['contagem'] = df_reg['total']

                    chart_data = [
                        {
                            'chart_type': 'fornecedores_por_regiao',
                            'dimension': 'suppliers',
                            'region_name': row['region_name'],
                            'region_type': 'state',
                            'total': int(row['total']),
                            'contagem': int(row['contagem']),
                            'percentual': float(row['percentual'])
                        }
                        for _, row in df_reg.iterrows()
                    ]

                    if chart_data:
                        try:
                            v2_count = self.repository.write_star_regional(self.client_id, chart_data)
                            logger.info(f"  ✓ Written {v2_count} regional points to analytics_v2 (fornecedores)")
                        except Exception as e:
                            logger.error(f"  ✗ Failed to write v2 regional (fornecedores): {e}", exc_info=True)

            # Clientes por região (state)
            if 'receiver_nome' in self.df.columns:
                state_col = None
                for col in ['receiverstateuf', 'receiver_estado', 'receiver_state']:
                    if col in self.df.columns:
                        state_col = col
                        break

                if state_col:
                    df_reg = self.df.groupby(state_col)['receiver_nome'].nunique().reset_index()
                    df_reg.rename(columns={state_col: 'region_name', 'receiver_nome': 'total'}, inplace=True)
                    total = df_reg['total'].sum() or 1
                    df_reg['percentual'] = (df_reg['total'] / total * 100).round(2)
                    df_reg['contagem'] = df_reg['total']

                    chart_data = [
                        {
                            'chart_type': 'clientes_por_regiao',
                            'dimension': 'customers',
                            'region_name': row['region_name'],
                            'region_type': 'state',
                            'total': int(row['total']),
                            'contagem': int(row['contagem']),
                            'percentual': float(row['percentual'])
                        }
                        for _, row in df_reg.iterrows()
                    ]

                    if chart_data:
                        try:
                            v2_count = self.repository.write_star_regional(self.client_id, chart_data)
                            logger.info(f"  ✓ Written {v2_count} regional points to analytics_v2 (clientes)")
                        except Exception as e:
                            logger.error(f"  ✗ Failed to write v2 regional (clientes): {e}", exc_info=True)

            # Pedidos por região (city)
            if 'emitter_cidade' in self.df.columns and 'order_id' in self.df.columns:
                df_reg = self.df.groupby('emitter_cidade')['order_id'].nunique().nlargest(10).reset_index()
                df_reg.rename(columns={'emitter_cidade': 'region_name', 'order_id': 'total'}, inplace=True)
                total = df_reg['total'].sum() or 1
                df_reg['percentual'] = (df_reg['total'] / total * 100).round(2)
                df_reg['contagem'] = df_reg['total']

                chart_data = [
                    {
                        'chart_type': 'pedidos_por_regiao',
                        'dimension': 'orders',
                        'region_name': row['region_name'],
                        'region_type': 'city',
                        'total': int(row['total']),
                        'contagem': int(row['contagem']),
                        'percentual': float(row['percentual'])
                    }
                    for _, row in df_reg.iterrows()
                ]

                if chart_data:
                    try:
                        v2_count = self.repository.write_star_regional(self.client_id, chart_data)
                        logger.info(f"  ✓ Written {v2_count} regional points to analytics_v2 (pedidos)")
                    except Exception as e:
                        logger.error(f"  ✗ Failed to write v2 regional (pedidos): {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to write regional charts: {e}", exc_info=True)

    def _write_last_orders(self) -> None:
        """Compute and write last 20 orders snapshot"""
        if self.df.empty:
            logger.warning("No data available for last orders")
            return

        required_cols = {'order_id', 'data_transacao', 'receiver_nome', 'valor_total_emitter', 'raw_product_description'}
        if not required_cols.issubset(self.df.columns):
            logger.warning(f"Missing required columns for last orders: {required_cols - set(self.df.columns)}")
            return

        try:
            # Build aggregation dict - include cpf_cnpj if available
            agg_dict = {
                'data_transacao': ('data_transacao', 'max'),
                'customer_name': ('receiver_nome', 'first'),
                'ticket_pedido': ('valor_total_emitter', 'sum'),
                'qtd_produtos': ('raw_product_description', 'nunique'),
            }

            # Add customer_cpf_cnpj if available in the dataframe
            if 'receiver_cpf_cnpj' in self.df.columns:
                agg_dict['customer_cpf_cnpj'] = ('receiver_cpf_cnpj', 'first')

            df_orders = self.df.groupby('order_id').agg(**agg_dict).reset_index()

            # Sort by date descending and take top 20
            df_orders = df_orders.sort_values('data_transacao', ascending=False).head(20).reset_index(drop=True)

            # Add rank
            df_orders['order_rank'] = df_orders.index + 1

            chart_data = [
                {
                    'order_id': row['order_id'],
                    'data_transacao': pd.Timestamp(row['data_transacao']).to_pydatetime() if pd.notna(row['data_transacao']) else None,
                    'customer_cpf_cnpj': row.get('customer_cpf_cnpj', None),
                    'customer_name': row.get('customer_name', None),
                    'ticket_pedido': float(row['ticket_pedido']),
                    'qtd_produtos': int(row['qtd_produtos']),
                    'order_rank': int(row['order_rank'])
                }
                for _, row in df_orders.iterrows()
            ]

            if chart_data:
                try:
                    v2_count = self.repository.write_star_last_orders(self.client_id, chart_data)
                    logger.info(f"  ✓ Written {v2_count} last orders to analytics_v2")
                except Exception as e:
                    logger.error(f"  ✗ Failed to write v2 last_orders: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to write last orders: {e}", exc_info=True)

    # ---
    # Helpers: prefer materialized views when available
    # ---
    def _load_mv_product_summary(self) -> pd.DataFrame:
        """Load analytics_v2.mv_product_summary into a DataFrame (returns empty DF on error)."""
        try:
            conn = self.repository.db_session
            q = "SELECT * FROM analytics_v2.mv_product_summary WHERE client_id = :client_id"
            res = conn.execute(text(q), {"client_id": self.client_id})
            rows = res.fetchall()
            cols = res.keys()
            if not rows:
                return pd.DataFrame(columns=cols)
            return pd.DataFrame(rows, columns=cols)
        except Exception as e:
            logger.warning(f"Could not load mv_product_summary: {e}")
            return pd.DataFrame()

    def _load_mv_customer_summary(self) -> pd.DataFrame:
        """Load analytics_v2.mv_customer_summary into a DataFrame (returns empty DF on error)."""
        try:
            conn = self.repository.db_session
            q = "SELECT * FROM analytics_v2.mv_customer_summary WHERE client_id = :client_id"
            res = conn.execute(text(q), {"client_id": self.client_id})
            rows = res.fetchall()
            cols = res.keys()
            if not rows:
                return pd.DataFrame(columns=cols)
            return pd.DataFrame(rows, columns=cols)
        except Exception as e:
            logger.warning(f"Could not load mv_customer_summary: {e}")
            return pd.DataFrame()

    def _load_mv_monthly_sales_trend(self) -> pd.DataFrame:
        """Load analytics_v2.mv_monthly_sales_trend into a DataFrame (returns empty DF on error)."""
        try:
            conn = self.repository.db_session
            q = "SELECT * FROM analytics_v2.mv_monthly_sales_trend WHERE client_id = :client_id ORDER BY ano_mes"
            res = conn.execute(text(q), {"client_id": self.client_id})
            rows = res.fetchall()
            cols = res.keys()
            if not rows:
                return pd.DataFrame(columns=cols)
            return pd.DataFrame(rows, columns=cols)
        except Exception as e:
            logger.warning(f"Could not load mv_monthly_sales_trend: {e}")
            return pd.DataFrame()

    # ---
    # NÍVEL 1 (HOME)
    # ---
    def get_home_metrics(self) -> HomeMetricsResponse:
        """Returns home metrics as Pydantic model for validation."""
        logger.info(f"[MetricService] Calculando métricas Nível 1 para {self.client_id}")

        # Build scorecards defensively, always returning required keys
        scorecards_data = {
            "receita_total": 0.0,
            "total_fornecedores": 0,
            "total_produtos": 0,
            "total_regioes": 0,
            "total_clientes": 0,
            "total_pedidos": 0,
        }

        if not self.df.empty:
            if 'valor_total_emitter' in self.df.columns:
                scorecards_data["receita_total"] = float(self.df['valor_total_emitter'].sum())

            if 'emitter_nome' in self.df.columns:
                scorecards_data["total_fornecedores"] = int(self.df['emitter_nome'].nunique())

            if 'raw_product_description' in self.df.columns:
                scorecards_data["total_produtos"] = int(self.df['raw_product_description'].nunique())

            # Calculate total unique regions (use state/UF for broader coverage)
            scorecards_data["total_regioes"] = self._calculate_total_regions()

            if 'receiver_nome' in self.df.columns:
                scorecards_data["total_clientes"] = int(self.df['receiver_nome'].nunique())

            if 'order_id' in self.df.columns:
                scorecards_data["total_pedidos"] = int(self.df['order_id'].nunique())

        # Build chart data defensively
        chart_data_receita_mes = []
        if not self.df.empty and 'valor_total_emitter' in self.df.columns and 'ano_mes' in self.df.columns:
            receita_por_mes_df = self.df.groupby('ano_mes')['valor_total_emitter'].sum().sort_index()
            chart_data_receita_mes = [
                ChartDataPoint(name=index, receita=float(value))
                for index, value in receita_por_mes_df.items()
            ]

        charts = [
            ChartData(
                id="receita-por-mes",
                title="Receita Total por Mês",
                data=chart_data_receita_mes
            )
        ] if chart_data_receita_mes else []

        return HomeMetricsResponse(
            scorecards=HomeScorecards(**scorecards_data),
            charts=charts
        )

    # ---
    # NÍVEL 2 (MÓDULOS) - (Atualizado para Q2)
    # ---

    def get_fornecedores_overview(self) -> FornecedoresOverviewResponse:
        """Returns fornecedores overview as Pydantic model for validation."""
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Fornecedores) para {self.client_id}")

        # 1. Usa o Helper pré-calculado
        df_fornecedores_agg = self.df_fornecedores_agg

        # Prefer materialized view data when available (conservative mapping)
        try:
            mv_prod = self._load_mv_product_summary()
            if not mv_prod.empty:
                # if MV contains supplier-level rows, map supplier_name -> nome
                if 'supplier_name' in mv_prod.columns:
                    df_fornecedores_agg = mv_prod.rename(columns={'supplier_name': 'nome'})
                elif 'emitter_nome' in mv_prod.columns:
                    df_fornecedores_agg = mv_prod.rename(columns={'emitter_nome': 'nome'})
                # ensure revenue column exists under expected name
                if 'receita_total' not in df_fornecedores_agg.columns and 'total_revenue' in mv_prod.columns:
                    df_fornecedores_agg['receita_total'] = mv_prod['total_revenue']
        except Exception:
            logger.debug("Failed to prefer mv_product_summary for fornecedores; using computed aggregation")

        # 2. Métricas Adicionais (com checks defensivos)...
        df_fornecedores_tempo = pd.DataFrame()
        if 'data_transacao' in self.df.columns and 'emitter_nome' in self.df.columns and 'ano_mes' in self.df.columns:
            df_fornecedores_tempo = self.df.sort_values('data_transacao').drop_duplicates('emitter_nome')
            df_fornecedores_tempo = df_fornecedores_tempo.groupby('ano_mes').size().cumsum().reset_index(name='total_cumulativo')
            # Rename column to 'name' for ChartDataPoint schema
            df_fornecedores_tempo.rename(columns={'ano_mes': 'name'}, inplace=True)
        else:
            logger.warning("Missing columns for fornecedores_tempo; skipping")

        df_top_produtos = self.df_produtos_agg.sort_values('receita_total', ascending=False).head(10) if not self.df_produtos_agg.empty else pd.DataFrame()

        # Try multiple column names for state (emitterstateuf or emitter_estado)
        df_fornecedores_regiao = pd.DataFrame()
        state_col = None
        for col in ['emitterstateuf', 'emitter_estado', 'emitter_state']:
            if col in self.df.columns:
                state_col = col
                break
        if state_col and 'emitter_nome' in self.df.columns:
            df_fornecedores_regiao = self.df.groupby(state_col)['emitter_nome'].nunique().reset_index(name='total')
            # Rename column to 'name' for ChartDataPoint schema
            df_fornecedores_regiao.rename(columns={state_col: 'name'}, inplace=True)
        else:
            logger.warning("Missing state column for fornecedores_regiao; skipping")

        # NOVO (Q2): Gráfico de Cohort (Tiers)
        df_cohort = df_fornecedores_agg.groupby('cluster_tier').size().reset_index(name='contagem')
        df_cohort['percentual'] = (df_cohort['contagem'] / df_cohort['contagem'].sum()) * 100
        # CORREÇÃO: Renomeia a coluna para corresponder ao schema ChartDataPoint
        df_cohort.rename(columns={'cluster_tier': 'name'}, inplace=True)

        # Calculate growth percentage using helper method
        crescimento_percentual = None
        if not self.df.empty and 'ano_mes' in self.df.columns and 'emitter_nome' in self.df.columns:
            crescimento_percentual = self._calculate_time_series_growth('ano_mes', 'emitter_nome')
            if crescimento_percentual is not None:
                logger.info(f"  ✓ Fornecedores growth: {crescimento_percentual}%")

            # Fallback to original logic if helper returns None
            if crescimento_percentual is None:
                # Agrupar por fornecedor e mês de primeira venda
                df_novos_fornecedores = self.df.sort_values('data_transacao').drop_duplicates('emitter_nome')[['emitter_nome', 'ano_mes']]
                fornecedores_por_mes = df_novos_fornecedores.groupby('ano_mes').size()

                if len(fornecedores_por_mes) >= 2:
                    # Pega os dois últimos meses
                    mes_atual = fornecedores_por_mes.iloc[-1]
                    mes_anterior = fornecedores_por_mes.iloc[-2]

                    if mes_anterior > 0:
                        crescimento_percentual = float(((mes_atual - mes_anterior) / mes_anterior) * 100)

        # Convert dataframes to Pydantic objects
        chart_fornecedores_no_tempo = [
            ChartDataPoint(**record)
            for record in df_fornecedores_tempo.to_dict('records')
        ] if not df_fornecedores_tempo.empty else []

        chart_fornecedores_por_regiao = [
            ChartDataPoint(**record)
            for record in df_fornecedores_regiao.to_dict('records')
        ] if not df_fornecedores_regiao.empty else []

        chart_cohort_fornecedores = [
            ChartDataPoint(**record)
            for record in df_cohort.to_dict('records')
        ]

        ranking_por_receita = [
            RankingItem(**record)
            for record in df_fornecedores_agg.sort_values('receita_total', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_ticket_medio = [
            RankingItem(**record)
            for record in df_fornecedores_agg.sort_values('ticket_medio', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_qtd_media = [
            RankingItem(**record)
            for record in df_fornecedores_agg.sort_values('qtd_media_por_pedido', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_frequencia = [
            RankingItem(**record)
            for record in df_fornecedores_agg.sort_values('frequencia_pedidos_mes', ascending=False).head(10).to_dict('records')
        ]

        ranking_produtos_mais_vendidos = df_top_produtos[['nome', 'receita_total', 'valor_unitario_medio']].to_dict('records')

        return FornecedoresOverviewResponse(
            scorecard_total_fornecedores=int(df_fornecedores_agg.shape[0]),
            scorecard_crescimento_percentual=crescimento_percentual,
            chart_fornecedores_no_tempo=chart_fornecedores_no_tempo,
            chart_fornecedores_por_regiao=chart_fornecedores_por_regiao,
            chart_cohort_fornecedores=chart_cohort_fornecedores,
            ranking_por_receita=ranking_por_receita,
            ranking_por_ticket_medio=ranking_por_ticket_medio,
            ranking_por_qtd_media=ranking_por_qtd_media,
            ranking_por_frequencia=ranking_por_frequencia,
            ranking_produtos_mais_vendidos=ranking_produtos_mais_vendidos,
        )

    def get_clientes_overview(self) -> ClientesOverviewResponse:
        """Returns clientes overview as Pydantic model for validation."""
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Clientes) para {self.client_id}")
        logger.info(f"[DEBUG] self.df shape: {self.df.shape}, columns: {list(self.df.columns)[:10]}...")
        logger.info(f"[DEBUG] df_clientes_agg shape: {self.df_clientes_agg.shape}, columns: {list(self.df_clientes_agg.columns)}")

        # 1. Usa o Helper pré-calculado
        df_clientes_agg = self.df_clientes_agg

        # Prefer materialized view customer summary when available
        try:
            mv_cust = self._load_mv_customer_summary()
            if not mv_cust.empty:
                rename_map = {}
                for src in ['customer_name', 'name', 'cliente_nome', 'customer']:
                    if src in mv_cust.columns:
                        rename_map[src] = 'nome'
                        break
                if 'receita_total' not in mv_cust.columns and 'total_revenue' in mv_cust.columns:
                    mv_cust['receita_total'] = mv_cust['total_revenue']
                if 'frequencia_pedidos_mes' not in mv_cust.columns and 'frequency_per_month' in mv_cust.columns:
                    mv_cust['frequencia_pedidos_mes'] = mv_cust['frequency_per_month']
                if 'recencia_dias' not in mv_cust.columns and 'recency_days' in mv_cust.columns:
                    mv_cust['recencia_dias'] = mv_cust['recency_days']
                if rename_map:
                    df_clientes_agg = mv_cust.rename(columns=rename_map)
        except Exception:
            logger.debug("Failed to prefer mv_customer_summary for clientes; using computed aggregation")

        # 2. Métricas Adicionais (com checks defensivos)...
        df_clientes_regiao = pd.DataFrame()
        state_col = None
        for col in ['receiverstateuf', 'receiver_estado', 'receiver_state']:
            if col in self.df.columns:
                state_col = col
                break

        logger.info(f"[DEBUG] State column search result: state_col={state_col}, receiver_nome in columns: {'receiver_nome' in self.df.columns}")

        if state_col and 'receiver_nome' in self.df.columns:
            df_clientes_regiao = self.df.groupby(state_col)['receiver_nome'].nunique().reset_index(name='contagem')
            total_clientes_regiao = df_clientes_regiao['contagem'].sum()
            df_clientes_regiao['percentual'] = (df_clientes_regiao['contagem'] / total_clientes_regiao) * 100
            # Rename column to 'name' for ChartDataPoint schema
            df_clientes_regiao.rename(columns={state_col: 'name'}, inplace=True)
            logger.info(f"[DEBUG] chart_clientes_por_regiao generated: {len(df_clientes_regiao)} regions")
            logger.info(f"[DEBUG] chart_clientes_por_regiao sample: {df_clientes_regiao.head(3).to_dict('records')}")
        else:
            logger.warning(f"⚠️  Missing state column for clientes_regiao; skipping. state_col={state_col}, has receiver_nome={'receiver_nome' in self.df.columns}")

        # NOVO (Q2): Gráfico de Cohort (Tiers)
        logger.info(f"[DEBUG] Checking cluster_tier: 'cluster_tier' in df_clientes_agg.columns = {'cluster_tier' in df_clientes_agg.columns}")
        if 'cluster_tier' in df_clientes_agg.columns:
            df_cohort = df_clientes_agg.groupby('cluster_tier').size().reset_index(name='contagem')
            df_cohort['percentual'] = (df_cohort['contagem'] / df_cohort['contagem'].sum()) * 100
            # CORREÇÃO: Renomeia a coluna para corresponder ao schema ChartDataPoint
            df_cohort.rename(columns={'cluster_tier': 'name'}, inplace=True)
            logger.info(f"[DEBUG] chart_cohort_clientes generated: {len(df_cohort)} tiers")
            logger.info(f"[DEBUG] chart_cohort_clientes data: {df_cohort.to_dict('records')}")
        else:
            df_cohort = pd.DataFrame()
            logger.warning(f"⚠️  Missing cluster_tier column in df_clientes_agg; cohort chart will be empty")

        # Calculate growth percentage using helper method
        crescimento_percentual = None
        if not self.df.empty and 'ano_mes' in self.df.columns and 'receiver_nome' in self.df.columns:
            crescimento_percentual = self._calculate_time_series_growth('ano_mes', 'receiver_nome')
            if crescimento_percentual is not None:
                logger.info(f"  ✓ Clientes growth: {crescimento_percentual}%")

            # Fallback to original logic if helper returns None
            if crescimento_percentual is None:
                # Agrupar por cliente e mês de primeira venda
                df_novos_clientes = self.df.sort_values('data_transacao').drop_duplicates('receiver_nome')[['receiver_nome', 'ano_mes']]
                clientes_por_mes = df_novos_clientes.groupby('ano_mes').size()

                if len(clientes_por_mes) >= 2:
                    # Pega os dois últimos meses
                    mes_atual = clientes_por_mes.iloc[-1]
                    mes_anterior = clientes_por_mes.iloc[-2]

                    if mes_anterior > 0:
                        crescimento_percentual = float(((mes_atual - mes_anterior) / mes_anterior) * 100)

        # Convert dataframes to Pydantic objects
        chart_clientes_por_regiao = [
            ChartDataPoint(**record)
            for record in df_clientes_regiao.to_dict('records')
        ] if not df_clientes_regiao.empty else []

        chart_cohort_clientes = [
            ChartDataPoint(**record)
            for record in df_cohort.to_dict('records')
        ] if not df_cohort.empty else []

        ranking_por_receita = [
            RankingItem(**record)
            for record in df_clientes_agg.sort_values('receita_total', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_ticket_medio = [
            RankingItem(**record)
            for record in df_clientes_agg.sort_values('ticket_medio', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_qtd_pedidos = [
            RankingItem(**record)
            for record in df_clientes_agg.sort_values('num_pedidos_unicos', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_cluster_vizu = [
            RankingItem(**record)
            for record in df_clientes_agg.sort_values('cluster_score', ascending=False).head(10).to_dict('records')
        ]

        return ClientesOverviewResponse(
            scorecard_total_clientes=int(df_clientes_agg.shape[0]),
            scorecard_ticket_medio_geral=float(df_clientes_agg['ticket_medio'].mean()) if not df_clientes_agg['ticket_medio'].empty else 0.0,
            scorecard_frequencia_media_geral=float(df_clientes_agg['frequencia_pedidos_mes'].mean()) if not df_clientes_agg['frequencia_pedidos_mes'].empty else 0.0,
            scorecard_crescimento_percentual=crescimento_percentual,
            chart_clientes_por_regiao=chart_clientes_por_regiao,
            chart_cohort_clientes=chart_cohort_clientes,
            ranking_por_receita=ranking_por_receita,
            ranking_por_ticket_medio=ranking_por_ticket_medio,
            ranking_por_qtd_pedidos=ranking_por_qtd_pedidos,
            ranking_por_cluster_vizu=ranking_por_cluster_vizu,
        )

        logger.info(f"[DEBUG] Response chart lengths - regiao: {len(chart_clientes_por_regiao)}, cohort: {len(chart_cohort_clientes)}")
        logger.info(f"[DEBUG] Response ranking lengths - receita: {len(ranking_por_receita)}, ticket: {len(ranking_por_ticket_medio)}")

    def get_produtos_overview(self) -> ProdutosOverviewResponse:
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Produtos) para {self.client_id}")

        # 1. Usa o Helper pré-calculado
        df_produtos_agg = self.df_produtos_agg

        # Prefer materialized view product summary when available
        try:
            mv_prod = self._load_mv_product_summary()
            if not mv_prod.empty:
                rename_map = {}
                for src in ['product_name', 'nome', 'raw_product_description']:
                    if src in mv_prod.columns:
                        rename_map[src] = 'nome'
                        break
                if 'receita_total' not in mv_prod.columns and 'total_revenue' in mv_prod.columns:
                    mv_prod['receita_total'] = mv_prod['total_revenue']
                if 'quantidade_total' not in mv_prod.columns and 'total_quantity' in mv_prod.columns:
                    mv_prod['quantidade_total'] = mv_prod['total_quantity']
                if 'valor_unitario_medio' not in mv_prod.columns and 'avg_price' in mv_prod.columns:
                    mv_prod['valor_unitario_medio'] = mv_prod['avg_price']
                if rename_map:
                    df_produtos_agg = mv_prod.rename(columns=rename_map)
        except Exception:
            logger.debug("Failed to prefer mv_product_summary for produtos; using computed aggregation")

        # Convert to specific product ranking schemas (simpler than RankingItem)
        from analytics_api.schemas.metrics import ProdutoRankingReceita, ProdutoRankingVolume, ProdutoRankingTicket

        ranking_por_receita = [
            ProdutoRankingReceita(
                nome=record['nome'],
                receita_total=record['receita_total'],
                valor_unitario_medio=record['valor_unitario_medio']
            )
            for record in df_produtos_agg.sort_values('receita_total', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_volume = [
            ProdutoRankingVolume(
                nome=record['nome'],
                quantidade_total=record['quantidade_total'],
                valor_unitario_medio=record['valor_unitario_medio']
            )
            for record in df_produtos_agg.sort_values('quantidade_total', ascending=False).head(10).to_dict('records')
        ]

        ranking_por_ticket_medio = [
            ProdutoRankingTicket(
                nome=record['nome'],
                ticket_medio=record['ticket_medio'],
                valor_unitario_medio=record['valor_unitario_medio']
            )
            for record in df_produtos_agg.sort_values('ticket_medio', ascending=False).head(10).to_dict('records')
        ]

        return ProdutosOverviewResponse(
            scorecard_total_itens_unicos=int(df_produtos_agg.shape[0]),
            ranking_por_receita=ranking_por_receita,
            ranking_por_volume=ranking_por_volume,
            ranking_por_ticket_medio=ranking_por_ticket_medio,
        )

    def get_pedidos_overview(self) -> PedidosOverviewResponse:
        # ... (sem mudanças significativas, código da v1) ...
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Pedidos) para {self.client_id}")
        df_pedidos_agg = self.df.groupby('order_id').agg(
            data_transacao=('data_transacao', 'first'),
            id_cliente=('receiver_nome', 'first'),
            ticket_pedido=('valor_total_emitter', 'sum'),
            qtd_produtos=('raw_product_description', 'nunique')
        ).reset_index()
        pedidos_por_cliente = self.df.groupby('receiver_nome')['order_id'].nunique()
        taxa_recorrencia = float((pedidos_por_cliente > 1).mean()) * 100
        recencia_media_dias = self.df.sort_values('data_transacao')['data_transacao'].diff().dt.days.mean()

        ranking_pedidos_por_regiao = [
            ChartDataPoint(**record)
            for record in self.df.groupby('emitter_cidade')['order_id'].nunique().nlargest(10).reset_index(name='contagem').rename(columns={'emitter_cidade': 'name'}).to_dict('records')
        ]

        ultimos_pedidos = [
            PedidoItem(**record)
            for record in df_pedidos_agg.sort_values('data_transacao', ascending=False).head(20).to_dict('records')
        ]

        return PedidosOverviewResponse(
            scorecard_ticket_medio_por_pedido=float(df_pedidos_agg['ticket_pedido'].mean()),
            scorecard_qtd_media_produtos_por_pedido=float(df_pedidos_agg['qtd_produtos'].mean()),
            scorecard_taxa_recorrencia_clientes_perc=taxa_recorrencia,
            scorecard_recencia_media_entre_pedidos_dias=float(recencia_media_dias),
            ranking_pedidos_por_regiao=ranking_pedidos_por_regiao,
            ultimos_pedidos=ultimos_pedidos
        )

    # ---
    # NÍVEL 3 (DETALHE) - (Atualizado para Q3 e Q4)
    # ---

    def get_fornecedor_details(self, nome_fornecedor: str) -> FornecedorDetailResponse:
        logger.info(f"[MetricService] Loading fornecedor details from star schema for: {nome_fornecedor}")

        # Get supplier metadata from dim_supplier
        supplier = self.repository.get_supplier_detail(self.client_id, nome_fornecedor)
        if not supplier:
            raise ValueError(f"Fornecedor não encontrado: {nome_fornecedor}")

        dados_cadastrais = CadastralData(
            emitter_nome=supplier.get('name'),
            emitter_cnpj=supplier.get('cnpj'),
            emitter_telefone=supplier.get('telefone'),
            emitter_estado=supplier.get('endereco_uf'),
            emitter_cidade=supplier.get('endereco_cidade'),
        )

        # Aggregate top customers and products for this supplier from fact_sales
        try:
            conn = self.repository.db_session

            # Top customers by revenue
            q_customers = """
                SELECT c.name as nome,
                       c.cpf_cnpj as customer_cpf_cnpj,
                       COUNT(DISTINCT f.order_id) as num_pedidos_unicos,
                       COALESCE(SUM(f.valor_total),0) as receita_total,
                       COALESCE(SUM(f.quantidade),0) as quantidade_total,
                       MIN(f.data_transacao) as primeira_venda,
                       MAX(f.data_transacao) as ultima_venda
                FROM analytics_v2.fact_sales f
                JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                WHERE s.client_id = :client_id AND s.name = :supplier_name
                GROUP BY c.name, c.cpf_cnpj
                ORDER BY receita_total DESC
                LIMIT 5
            """
            res = conn.execute(text(q_customers), {"client_id": self.client_id, "supplier_name": nome_fornecedor})
            rows = res.fetchall()
            cols = res.keys()
            clientes_por_receita = []
            for r in rows:
                d = dict(zip(cols, r))
                clientes_por_receita.append(RankingItem(
                    nome=d.get('nome') or '',
                    receita_total=float(d.get('receita_total') or 0),
                    quantidade_total=float(d.get('quantidade_total') or 0),
                    num_pedidos_unicos=int(d.get('num_pedidos_unicos') or 0),
                    primeira_venda=d.get('primeira_venda'),
                    ultima_venda=d.get('ultima_venda'),
                    ticket_medio=0.0,
                    qtd_media_por_pedido=0.0,
                    frequencia_pedidos_mes=0.0,
                    recencia_dias=0,
                    valor_unitario_medio=0.0,
                    cluster_score=0.0,
                    cluster_tier="",
                ))

            # Top products by revenue for this supplier
            q_products = """
                SELECT p.product_name as nome,
                       COUNT(DISTINCT f.order_id) as num_pedidos,
                       COALESCE(SUM(f.valor_total),0) as receita_total,
                       COALESCE(SUM(f.quantidade),0) as quantidade_total,
                       MIN(f.data_transacao) as primeira_venda,
                       MAX(f.data_transacao) as ultima_venda,
                       AVG(f.valor_total) as valor_unitario_medio
                FROM analytics_v2.fact_sales f
                JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                WHERE s.client_id = :client_id AND s.name = :supplier_name
                GROUP BY p.product_name
                ORDER BY receita_total DESC
                LIMIT 5
            """
            res2 = conn.execute(text(q_products), {"client_id": self.client_id, "supplier_name": nome_fornecedor})
            rows2 = res2.fetchall()
            cols2 = res2.keys()
            produtos_por_receita = []
            for r in rows2:
                d = dict(zip(cols2, r))
                produtos_por_receita.append(RankingItem(
                    nome=d.get('nome') or '',
                    receita_total=float(d.get('receita_total') or 0),
                    quantidade_total=float(d.get('quantidade_total') or 0),
                    num_pedidos_unicos=int(d.get('num_pedidos') or 0),
                    primeira_venda=d.get('primeira_venda'),
                    ultima_venda=d.get('ultima_venda'),
                    ticket_medio=float(d.get('valor_unitario_medio') or 0),
                    qtd_media_por_pedido=0.0,
                    frequencia_pedidos_mes=0.0,
                    recencia_dias=0,
                    valor_unitario_medio=float(d.get('valor_unitario_medio') or 0),
                    cluster_score=0.0,
                    cluster_tier="",
                ))

            # Regions by revenue for this supplier
            q_regions = """
                SELECT c.endereco_cidade as nome,
                       COALESCE(SUM(f.valor_total),0) as receita_total,
                       COUNT(DISTINCT f.order_id) as num_pedidos
                FROM analytics_v2.fact_sales f
                JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
                WHERE s.client_id = :client_id AND s.name = :supplier_name
                GROUP BY c.endereco_cidade
                ORDER BY receita_total DESC
                LIMIT 5
            """
            res3 = conn.execute(text(q_regions), {"client_id": self.client_id, "supplier_name": nome_fornecedor})
            rows3 = res3.fetchall()
            cols3 = res3.keys()
            regioes_por_receita = []
            for r in rows3:
                d = dict(zip(cols3, r))
                regioes_por_receita.append(RankingItem(
                    nome=d.get('nome') or '',
                    receita_total=float(d.get('receita_total') or 0),
                    quantidade_total=0.0,
                    num_pedidos_unicos=int(d.get('num_pedidos') or 0),
                    primeira_venda=None,
                    ultima_venda=None,
                    ticket_medio=0.0,
                    qtd_media_por_pedido=0.0,
                    frequencia_pedidos_mes=0.0,
                    recencia_dias=0,
                    valor_unitario_medio=0.0,
                    cluster_score=0.0,
                    cluster_tier="",
                ))

        except Exception as e:
            logger.error(f"Failed to build fornecedor rankings from star schema: {e}", exc_info=True)
            clientes_por_receita = []
            produtos_por_receita = []
            regioes_por_receita = []

        return FornecedorDetailResponse(
            dados_cadastrais=dados_cadastrais,
            rankings_internos={
                "clientes_por_receita": clientes_por_receita,
                "produtos_por_receita": produtos_por_receita,
                "regioes_por_receita": regioes_por_receita,
            }
        )


    def get_cliente_details(self, nome_cliente: str) -> ClienteDetailResponse:
        logger.info(f"[MetricService] Loading cliente details from star schema for: {nome_cliente}")

        # Use the repository to read from analytics_v2.dim_customer
        customer = self.repository.get_customer_detail(self.client_id, nome_cliente)
        if not customer:
            raise ValueError(f"Cliente não encontrado: {nome_cliente}")

        # Map cadastral data
        dados_cadastrais = CadastralData(
            receiver_nome=customer.get('name') or customer.get('customer_name') or nome_cliente,
            receiver_cnpj=customer.get('cpf_cnpj') or customer.get('customer_cpf_cnpj'),
            receiver_telefone=customer.get('telefone'),
            receiver_estado=customer.get('endereco_uf') or customer.get('endereco_estado'),
            receiver_cidade=customer.get('endereco_cidade') or customer.get('endereco_city'),
        )

        # Build scorecard from dimension fields
        primeira_venda = customer.get('lifetime_start_date') or customer.get('primeira_venda')
        ultima_venda = customer.get('lifetime_end_date') or customer.get('ultima_venda')

        scorecard_obj = RankingItem(
            nome=dados_cadastrais.receiver_nome or nome_cliente,
            receita_total=float(customer.get('total_revenue') or customer.get('lifetime_value') or 0),
            quantidade_total=float(customer.get('total_quantity') or 0),
            num_pedidos_unicos=int(customer.get('total_orders') or customer.get('num_pedidos_unicos') or 0),
            primeira_venda=primeira_venda,
            ultima_venda=ultima_venda,
            ticket_medio=float(customer.get('avg_order_value') or customer.get('ticket_medio') or 0),
            qtd_media_por_pedido=float((customer.get('total_quantity') or 0) / (customer.get('total_orders') or 1)),
            frequencia_pedidos_mes=float(customer.get('frequency_per_month') or customer.get('frequencia_pedidos_mes') or 0),
            recencia_dias=int(customer.get('recency_days') or customer.get('recencia_dias') or 0),
            valor_unitario_medio=float(customer.get('valor_unitario_medio') or 0),
            cluster_score=float(customer.get('cluster_score') or 0),
            cluster_tier=customer.get('cluster_tier') or "",
        )

        # Fetch mix de produtos from star view v_customer_products
        customer_cpf = customer.get('cpf_cnpj') or customer.get('customer_cpf_cnpj')
        mix_products = []
        if customer_cpf:
            try:
                products = self.repository.get_v2_customer_products(self.client_id, customer_cpf, limit=10) or []
                mix_products = [
                    RankingItem(
                        nome=p.get('nome') or p.get('product_name') or '',
                        receita_total=float(p.get('receita_total', 0)),
                        quantidade_total=float(p.get('quantidade_total', 0)),
                        num_pedidos_unicos=int(p.get('num_pedidos', 0)),
                        primeira_venda=p.get('primeira_compra'),
                        ultima_venda=p.get('ultima_compra'),
                        ticket_medio=0.0,
                        qtd_media_por_pedido=0.0,
                        frequencia_pedidos_mes=0.0,
                        recencia_dias=0,
                        valor_unitario_medio=float(p.get('valor_unitario_medio', 0)),
                        cluster_score=0.0,
                        cluster_tier="",
                    )
                    for p in products
                ]
            except Exception:
                mix_products = []

        return ClienteDetailResponse(
            dados_cadastrais=dados_cadastrais,
            scorecards=scorecard_obj,
            rankings_internos={
                "mix_de_produtos_por_receita": mix_products,
            }
        )

    def get_produto_details(self, nome_produto: str) -> ProdutoDetailResponse:
        logger.info(f"[MetricService] Loading produto details from star schema for: {nome_produto}")

        # Get product metadata
        product = self.repository.get_product_detail(self.client_id, nome_produto)
        if not product:
            raise ValueError(f"Produto não encontrado: {nome_produto}")

        # Build scorecard
        scorecard_obj = RankingItem(
            nome=product.get('product_name') or nome_produto,
            receita_total=float(product.get('total_revenue') or 0),
            quantidade_total=float(product.get('total_quantity_sold') or 0),
            num_pedidos_unicos=int(product.get('number_of_orders') or 0),
            primeira_venda=product.get('last_sale_date'),
            ultima_venda=product.get('last_sale_date'),
            ticket_medio=float(product.get('avg_price') or 0),
            qtd_media_por_pedido=float(product.get('avg_quantity_per_order') or 0),
            frequencia_pedidos_mes=float(product.get('frequency_per_month') or 0),
            recencia_dias=int(product.get('recency_days') or 0),
            valor_unitario_medio=float(product.get('avg_price') or 0),
            cluster_score=float(product.get('cluster_score') or 0),
            cluster_tier=product.get('cluster_tier') or "",
        )

        # Aggregate top customers and regions for this product from fact_sales
        try:
            conn = self.repository.db_session

            q_customers = """
                SELECT c.name as nome,
                       c.cpf_cnpj as customer_cpf_cnpj,
                       COUNT(DISTINCT f.order_id) as num_pedidos_unicos,
                       COALESCE(SUM(f.valor_total),0) as receita_total,
                       COALESCE(SUM(f.quantidade),0) as quantidade_total,
                       MIN(f.data_transacao) as primeira_venda,
                       MAX(f.data_transacao) as ultima_venda
                FROM analytics_v2.fact_sales f
                JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                WHERE p.client_id = :client_id AND p.product_name = :product_name
                GROUP BY c.name, c.cpf_cnpj
                ORDER BY receita_total DESC
                LIMIT 5
            """
            res = conn.execute(text(q_customers), {"client_id": self.client_id, "product_name": nome_produto})
            rows = res.fetchall()
            cols = res.keys()
            clientes_por_receita = []
            for r in rows:
                d = dict(zip(cols, r))
                clientes_por_receita.append(RankingItem(
                    nome=d.get('nome') or '',
                    receita_total=float(d.get('receita_total') or 0),
                    quantidade_total=float(d.get('quantidade_total') or 0),
                    num_pedidos_unicos=int(d.get('num_pedidos_unicos') or 0),
                    primeira_venda=d.get('primeira_venda'),
                    ultima_venda=d.get('ultima_venda'),
                    ticket_medio=0.0,
                    qtd_media_por_pedido=0.0,
                    frequencia_pedidos_mes=0.0,
                    recencia_dias=0,
                    valor_unitario_medio=0.0,
                    cluster_score=0.0,
                    cluster_tier="",
                ))

            q_regions = """
                SELECT c.endereco_cidade as nome,
                       COALESCE(SUM(f.valor_total),0) as receita_total,
                       COUNT(DISTINCT f.order_id) as num_pedidos
                FROM analytics_v2.fact_sales f
                JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
                JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
                WHERE p.client_id = :client_id AND p.product_name = :product_name
                GROUP BY c.endereco_cidade
                ORDER BY receita_total DESC
                LIMIT 5
            """
            res2 = conn.execute(text(q_regions), {"client_id": self.client_id, "product_name": nome_produto})
            rows2 = res2.fetchall()
            cols2 = res2.keys()
            regioes_por_receita = []
            for r in rows2:
                d = dict(zip(cols2, r))
                regioes_por_receita.append(RankingItem(
                    nome=d.get('nome') or '',
                    receita_total=float(d.get('receita_total') or 0),
                    quantidade_total=0.0,
                    num_pedidos_unicos=int(d.get('num_pedidos') or 0),
                    primeira_venda=None,
                    ultima_venda=None,
                    ticket_medio=0.0,
                    qtd_media_por_pedido=0.0,
                    frequencia_pedidos_mes=0.0,
                    recencia_dias=0,
                    valor_unitario_medio=0.0,
                    cluster_score=0.0,
                    cluster_tier="",
                ))

        except Exception as e:
            logger.error(f"Failed to build produto rankings from star schema: {e}", exc_info=True)
            clientes_por_receita = []
            regioes_por_receita = []

        segmentos_de_clientes = []
        # Cohort segments can be derived from dim_customer clusters if needed

        return ProdutoDetailResponse(
            nome_produto=nome_produto,
            scorecards=scorecard_obj,
            charts={
                "segmentos_de_clientes": segmentos_de_clientes
            },
            rankings_internos={
                "clientes_por_receita": clientes_por_receita,
                "regioes_por_receita": regioes_por_receita,
            }
        )

    def get_pedido_details(self, order_id: str) -> PedidoDetailResponse:
        # ... (sem mudanças significativas, código da v1) ...
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Pedido: {order_id}")
        df_filtrado = self.df[self.df['order_id'] == order_id].copy()
        if df_filtrado.empty:
            raise ValueError(f"Pedido (order_id) não encontrado: {order_id}")

        cadastral_row = df_filtrado.iloc[0]
        dados_cliente = CadastralData(
            receiver_nome=str(cadastral_row.get('receiver_nome')),
            receiver_cnpj=cadastral_row.get('receiver_cnpj'),
            receiver_telefone=cadastral_row.get('receiver_telefone'),
            receiver_estado=cadastral_row.get('receiver_estado'),
            receiver_cidade=cadastral_row.get('receiver_cidade'),
        )

        itens_pedido = [
            PedidoItemDetalhe(
                raw_product_description=record.get('raw_product_description'),
                quantidade=float(record.get('quantidade', 0)),
                valor_unitario=float(record.get('valor_unitario', 0)),
                valor_total_emitter=float(record.get('valor_total_emitter', 0)),
            )
            for record in df_filtrado[
                ['raw_product_description', 'quantidade', 'valor_unitario', 'valor_total_emitter']
            ].to_dict('records')
        ]

        total_pedido = float(df_filtrado['valor_total_emitter'].sum())
        status_pedido = "Status Indisponível (OLTP)"  # Dado OLTP (Fora do Escopo)

        return PedidoDetailResponse(
            order_id=order_id,
            status_pedido=status_pedido,
            total_pedido=total_pedido,
            dados_cliente=dados_cliente,
            itens_pedido=itens_pedido
        )
