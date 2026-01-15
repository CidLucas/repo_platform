# src/analytics_api/services/metric_service.py
import logging

import numpy as np
import pandas as pd
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

    def __init__(self, repository: PostgresRepository, client_id: str, write_gold: bool = False):
        self.repository = repository
        self.client_id = client_id
        self.write_gold = write_gold  # controls whether we persist aggregates
        self.today = pd.Timestamp.now(tz='UTC')
        self.df = self.repository.get_silver_dataframe(client_id)

        # Flag to track if we've populated gold tables (avoid duplicate writes)
        self._gold_tables_written = False

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
        logger.info(f"  - Customers aggregated: {len(self.df_clientes_agg)} records")
        if logger.isEnabledFor(logging.DEBUG):
            DataQualityLogger.log_dataframe_describe(self.df_clientes_agg, "After Aggregation", "customers")

        self.df_fornecedores_agg = self._get_aggregated_metrics_by_dimension(self.df, 'emitter_nome')
        logger.info(f"  - Suppliers aggregated: {len(self.df_fornecedores_agg)} records")
        if logger.isEnabledFor(logging.DEBUG):
            DataQualityLogger.log_dataframe_describe(self.df_fornecedores_agg, "After Aggregation", "suppliers")

        # Products aggregation (use full metrics like customers/suppliers)
        self.df_produtos_agg = self._get_aggregated_metrics_by_dimension(self.df, 'raw_product_description')
        logger.info(f"  - Products aggregated: {len(self.df_produtos_agg)} records")
        if logger.isEnabledFor(logging.DEBUG):
            DataQualityLogger.log_dataframe_describe(self.df_produtos_agg, "After Aggregation", "products")

        # --- PERSIST TO GOLD TABLES ---
        # Only persist when explicitly allowed (ingestion/connector flows)
        if self.write_gold:
            self._write_all_gold_tables()


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

        if not agg_ops:
            logger.warning(f"No aggregatable columns found for {dimension_col}")
            return pd.DataFrame(columns=['nome', 'receita_total', 'quantidade_total', 'num_pedidos_unicos',
                                         'primeira_venda', 'ultima_venda', 'period_start', 'period_end',
                                         'ticket_medio', 'qtd_media_por_pedido',
                                         'frequencia_pedidos_mes', 'recencia_dias',
                                         'valor_unitario_medio', 'score_r', 'score_f', 'score_m',
                                         'cluster_score', 'cluster_tier'])

        agg_df = df.groupby(dimension_col).agg(**agg_ops).reset_index()

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
                agg_df['cluster_tier'] = pd.qcut(agg_df['cluster_score'], 4, labels=["D (Piores)", "C", "B", "A (Melhores)"])
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

    # =====================================================================
    # Write methods: Persist computed metrics to gold tables
    # =====================================================================

    def _write_all_gold_tables(self) -> None:
        """
        Write all computed metrics to gold tables.
        Called once after aggregations are computed to populate database.
        This ensures metrics are persisted and available to frontend via get_gold_* endpoints.
        """
        if not self.write_gold:
            logger.debug("write_gold=False; skipping gold table persistence")
            return

        if self._gold_tables_written or self.df.empty:
            logger.debug("Gold tables already written or no data available; skipping")
            return

        try:
            logger.info(f"💾 Writing aggregated data to gold tables for {self.client_id}...")

            # Write customers with data quality check
            if not self.df_clientes_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_clientes_agg)} customers...")
                if logger.isEnabledFor(logging.DEBUG):
                    DataQualityLogger.log_dataframe_describe(self.df_clientes_agg, "Before Write", "gold_customers")
                DataQualityLogger.log_dataframe_quality(self.df_clientes_agg, "analytics_gold_customers", self.client_id)

                # Add CPF/CNPJ from source if available
                customers_data = self.df_clientes_agg.to_dict('records')
                for customer in customers_data:
                    # Try to get CPF/CNPJ from original data
                    if 'receiver_cpf_cnpj' not in customer or pd.isna(customer.get('receiver_cpf_cnpj')):
                        nome = customer.get('nome')
                        if nome and 'receiver_nome' in self.df.columns:
                            match = self.df[self.df['receiver_nome'] == nome]
                            if not match.empty and 'receiver_cpf_cnpj' in match.columns:
                                cpf_cnpj = match['receiver_cpf_cnpj'].dropna().iloc[0] if not match['receiver_cpf_cnpj'].dropna().empty else None
                                customer['receiver_cpf_cnpj'] = cpf_cnpj

                self.repository.write_gold_customers(self.client_id, customers_data)
            else:
                logger.warning(f"  ⚠️  No customer data to write")

            # Write suppliers with data quality check
            if not self.df_fornecedores_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_fornecedores_agg)} suppliers...")
                if logger.isEnabledFor(logging.DEBUG):
                    DataQualityLogger.log_dataframe_describe(self.df_fornecedores_agg, "Before Write", "gold_suppliers")
                DataQualityLogger.log_dataframe_quality(self.df_fornecedores_agg, "analytics_gold_suppliers", self.client_id)

                # Add CNPJ from source if available
                suppliers_data = self.df_fornecedores_agg.to_dict('records')
                for supplier in suppliers_data:
                    if 'emitter_cnpj' not in supplier or pd.isna(supplier.get('emitter_cnpj')):
                        nome = supplier.get('nome')
                        if nome and 'emitter_nome' in self.df.columns:
                            match = self.df[self.df['emitter_nome'] == nome]
                            if not match.empty and 'emitter_cnpj' in match.columns:
                                cnpj = match['emitter_cnpj'].dropna().iloc[0] if not match['emitter_cnpj'].dropna().empty else None
                                supplier['emitter_cnpj'] = cnpj

                self.repository.write_gold_suppliers(self.client_id, suppliers_data)
            else:
                logger.warning(f"  ⚠️  No supplier data to write")

            # Write products with data quality check
            if not self.df_produtos_agg.empty:
                logger.info(f"  ➜ Writing {len(self.df_produtos_agg)} products...")
                if logger.isEnabledFor(logging.DEBUG):
                    DataQualityLogger.log_dataframe_describe(self.df_produtos_agg, "Before Write", "gold_products")
                DataQualityLogger.log_dataframe_quality(self.df_produtos_agg, "analytics_gold_products", self.client_id)
                self.repository.write_gold_products(
                    self.client_id,
                    self.df_produtos_agg.to_dict('records')
                )
            else:
                logger.warning(f"  ⚠️  No product data to write")

            # Write orders summary with data quality check
            if not self.df.empty and 'order_id' in self.df.columns:
                # Calculate period_start and period_end from data_transacao
                period_start = None
                period_end = None
                if 'data_transacao' in self.df.columns and not self.df['data_transacao'].isna().all():
                    period_start = self.df['data_transacao'].min()
                    period_end = self.df['data_transacao'].max()

                orders_metrics = {
                    "total_orders": int(self.df['order_id'].nunique()),
                    "total_revenue": float(self.df['valor_total_emitter'].sum()) if 'valor_total_emitter' in self.df.columns else 0,
                    "avg_order_value": float((self.df['valor_total_emitter'].sum() / self.df['order_id'].nunique())) if 'valor_total_emitter' in self.df.columns and self.df['order_id'].nunique() > 0 else 0,
                    "period_start": period_start,
                    "period_end": period_end,
                }
                logger.info(f"  ➜ Writing order summary: {orders_metrics['total_orders']} orders, revenue: {orders_metrics['total_revenue']:.2f}")
                DataQualityLogger.log_dict_quality(orders_metrics, "analytics_gold_orders", self.client_id)
                self.repository.write_gold_orders(self.client_id, orders_metrics)
            else:
                logger.warning(f"  ⚠️  No order data to write (missing order_id or empty df)")

            # Write chart data (time series, regional, last orders)
            self._write_gold_charts()

            self._gold_tables_written = True
            logger.info(f"✅ All gold tables written successfully for {self.client_id}")

        except Exception as e:
            logger.error(f"❌ Failed to write gold tables: {e}", exc_info=True)
            # Don't raise - let metrics still be computed even if persistence fails

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

    def _write_gold_charts(self) -> None:
        """
        Write precomputed chart data (time series, regional, last orders) to gold tables.
        This eliminates the need to load full Silver dataframe on every module page view.
        """
        try:
            logger.info(f"📊 Computing and writing chart data to gold tables...")

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

            # Write all time series data in a single batch
            if all_time_series_data:
                self.repository.write_gold_time_series(self.client_id, all_time_series_data)
                logger.info(f"  ✓ Written total of {len(all_time_series_data)} time series points to database")

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
                        self.repository.write_gold_regional(self.client_id, chart_data)
                        logger.info(f"  ✓ Written {len(chart_data)} fornecedores regional points")

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
                        self.repository.write_gold_regional(self.client_id, chart_data)
                        logger.info(f"  ✓ Written {len(chart_data)} clientes regional points")

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
                    self.repository.write_gold_regional(self.client_id, chart_data)
                    logger.info(f"  ✓ Written {len(chart_data)} pedidos regional points")

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
            df_orders = self.df.groupby('order_id').agg(
                data_transacao=('data_transacao', 'max'),
                id_cliente=('receiver_nome', 'first'),
                ticket_pedido=('valor_total_emitter', 'sum'),
                qtd_produtos=('raw_product_description', 'nunique'),
            ).reset_index()

            # Sort by date descending and take top 20
            df_orders = df_orders.sort_values('data_transacao', ascending=False).head(20).reset_index(drop=True)

            # Add rank
            df_orders['order_rank'] = df_orders.index + 1

            chart_data = [
                {
                    'order_id': row['order_id'],
                    'data_transacao': pd.Timestamp(row['data_transacao']).to_pydatetime() if pd.notna(row['data_transacao']) else None,  # Convert to Python datetime
                    'id_cliente': row['id_cliente'],
                    'ticket_pedido': float(row['ticket_pedido']),
                    'qtd_produtos': int(row['qtd_produtos']),
                    'order_rank': int(row['order_rank'])
                }
                for _, row in df_orders.iterrows()
            ]

            if chart_data:
                self.repository.write_gold_last_orders(self.client_id, chart_data)
                logger.info(f"  ✓ Written {len(chart_data)} last orders")

        except Exception as e:
            logger.error(f"Failed to write last orders: {e}", exc_info=True)

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
        # ... (sem mudanças significativas, código da v1) ...
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Fornecedor: {nome_fornecedor}")
        df_filtrado = self.df[self.df['emitter_nome'] == nome_fornecedor].copy()
        if df_filtrado.empty:
            raise ValueError(f"Fornecedor não encontrado: {nome_fornecedor}")

        cadastral_row = df_filtrado.iloc[0]
        dados_cadastrais = CadastralData(
            emitter_nome=str(cadastral_row.get('emitter_nome')),
            emitter_cnpj=cadastral_row.get('emitter_cnpj'),
            emitter_telefone=cadastral_row.get('emitter_telefone'),
            emitter_estado=cadastral_row.get('emitter_estado'),
            emitter_cidade=cadastral_row.get('emitter_cidade'),
        )

        df_agg_clientes = self._get_aggregated_metrics_by_dimension(df_filtrado, 'receiver_nome')
        df_agg_produtos = self._get_aggregated_metrics_by_dimension(df_filtrado, 'raw_product_description')
        df_agg_regioes = self._get_aggregated_metrics_by_dimension(df_filtrado, 'receiver_cidade')

        clientes_por_receita = [
            RankingItem(**record)
            for record in df_agg_clientes.sort_values('receita_total', ascending=False).head(5).to_dict('records')
        ]

        produtos_por_receita = [
            RankingItem(**record)
            for record in df_agg_produtos.sort_values('receita_total', ascending=False).head(5).to_dict('records')
        ]

        regioes_por_receita = [
            RankingItem(**record)
            for record in df_agg_regioes.sort_values('receita_total', ascending=False).head(5).to_dict('records')
        ]

        return FornecedorDetailResponse(
            dados_cadastrais=dados_cadastrais,
            rankings_internos={
                "clientes_por_receita": clientes_por_receita,
                "produtos_por_receita": produtos_por_receita,
                "regioes_por_receita": regioes_por_receita,
            }
        )


    def get_cliente_details(self, nome_cliente: str) -> ClienteDetailResponse:
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Cliente: {nome_cliente}")

        df_filtrado = self.df[self.df['receiver_nome'] == nome_cliente].copy()
        if df_filtrado.empty:
            raise ValueError(f"Cliente não encontrado: {nome_cliente}")

        cadastral_row = df_filtrado.iloc[0]
        dados_cadastrais = CadastralData(
            receiver_nome=str(cadastral_row.get('receiver_nome')),
            receiver_cnpj=cadastral_row.get('receiver_cnpj'),
            receiver_telefone=cadastral_row.get('receiver_telefone'),
            receiver_estado=cadastral_row.get('receiver_estado'),
            receiver_cidade=cadastral_row.get('receiver_cidade'),
        )

        # ATUALIZADO (Q3): Pega o scorecard completo (freq, ticket, tier)
        # Filtramos o DataFrame pré-calculado
        scorecards = self.df_clientes_agg[self.df_clientes_agg['nome'] == nome_cliente].to_dict('records')
        scorecard_obj = RankingItem(**scorecards[0]) if scorecards else None

        df_agg_produtos = self._get_aggregated_metrics_by_dimension(df_filtrado, 'raw_product_description')

        mix_de_produtos_por_receita = [
            RankingItem(**record)
            for record in df_agg_produtos.sort_values('receita_total', ascending=False).head(5).to_dict('records')
        ]

        return ClienteDetailResponse(
            dados_cadastrais=dados_cadastrais,
            scorecards=scorecard_obj,
            rankings_internos={
                "mix_de_produtos_por_receita": mix_de_produtos_por_receita,
            }
        )

    def get_produto_details(self, nome_produto: str) -> ProdutoDetailResponse:
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Produto: {nome_produto}")

        df_filtrado = self.df[self.df['raw_product_description'] == nome_produto].copy()
        if df_filtrado.empty:
            raise ValueError(f"Produto não encontrado: {nome_produto}")

        # ATUALIZADO (Q4): Pega o scorecard completo (freq, ticket)
        scorecards = self.df_produtos_agg[self.df_produtos_agg['nome'] == nome_produto].to_dict('records')
        scorecard_obj = RankingItem(**scorecards[0]) if scorecards else None

        df_agg_clientes = self._get_aggregated_metrics_by_dimension(df_filtrado, 'receiver_nome')
        df_agg_regioes = self._get_aggregated_metrics_by_dimension(df_filtrado, 'receiver_cidade')

        # NOVO (Q4): Gráfico dos segmentos de cliente que compram este produto
        # 1. Pega os clientes que compraram este produto
        clientes_do_produto = df_filtrado['receiver_nome'].unique()
        # 2. Filtra o DF de agregação de clientes
        df_clientes_filtrados = self.df_clientes_agg[self.df_clientes_agg['nome'].isin(clientes_do_produto)]
        # 3. Agrupa por Tier
        df_cohort_produto = df_clientes_filtrados.groupby('cluster_tier').size().reset_index(name='contagem')
        df_cohort_produto['percentual'] = (df_cohort_produto['contagem'] / df_cohort_produto['contagem'].sum()) * 100
        # CORREÇÃO: Renomeia a coluna para corresponder ao schema ChartDataPoint
        df_cohort_produto.rename(columns={'cluster_tier': 'name'}, inplace=True)

        segmentos_de_clientes = [
            ChartDataPoint(**record)
            for record in df_cohort_produto.to_dict('records')
        ]

        clientes_por_receita = [
            RankingItem(**record)
            for record in df_agg_clientes.sort_values('receita_total', ascending=False).head(5).to_dict('records')
        ]

        regioes_por_receita = [
            RankingItem(**record)
            for record in df_agg_regioes.sort_values('receita_total', ascending=False).head(5).to_dict('records')
        ]

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
