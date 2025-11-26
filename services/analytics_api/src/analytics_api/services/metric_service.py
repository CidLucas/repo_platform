# src/analytics_api/services/metric_service.py
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from analytics_api.data_access.postgres_repository import PostgresRepository

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
        self.df = self.repository.get_silver_dataframe(client_id)
        
        if self.df.empty:
            logger.warning(f"Nenhum dado encontrado na camada Prata para o client_id: {self.client_id}")

        # --- Pré-processamento Crítico ---
        self.df['data_transacao'] = pd.to_datetime(self.df['data_transacao'], utc=True)
        self.df['valor_total_emitter'] = pd.to_numeric(self.df['valor_total_emitter'])
        self.df['quantidade'] = pd.to_numeric(self.df['quantidade'])
        
        # ATUALIZADO (Q1): Converte valor_unitario para numérico
        self.df['valor_unitario'] = pd.to_numeric(self.df['valor_unitario'])

        self.df['ano_mes'] = self.df['data_transacao'].dt.to_period('M').astype(str)
        self.df['ano_semana'] = self.df['data_transacao'].dt.to_period('W').astype(str)

        # --- PRÉ-CÁLCULO DE COHORTS (Q2) ---
        # Pré-calculamos os tiers de *Clientes* e *Fornecedores*
        # para que possam ser usados em todos os módulos.
        self.df_clientes_agg = self._get_aggregated_metrics_by_dimension(self.df, 'receiver_nome')
        self.df_fornecedores_agg = self._get_aggregated_metrics_by_dimension(self.df, 'emitter_nome')
        self.df_produtos_agg = self._get_aggregated_metrics_by_dimension(self.df, 'raw_product_description')


    # ---
    # HELPER AGREGADOR (ATUALIZADO PARA Q1 e Q2)
    # ---
    
    def _get_aggregated_metrics_by_dimension(self, df: pd.DataFrame, dimension_col: str) -> pd.DataFrame:
        """
        O CÉREBRO agnóstico de Nível 2 e 3. (Atualizado v2)
        """
        if df.empty or dimension_col not in df.columns:
            cols = ['nome', 'receita_total', 'quantidade_total', 'num_pedidos_unicos',
                    'primeira_venda', 'ultima_venda', 'ticket_medio', 'qtd_media_por_pedido',
                    'frequencia_pedidos_mes', 'recencia_dias', 
                    'valor_unitario_medio', # (Q1)
                    'cluster_score', 'cluster_tier'] # (Q2)
            return pd.DataFrame(columns=cols)

        # 1. Agregação Primária
        agg_ops = {
            'receita_total': ('valor_total_emitter', 'sum'),
            'quantidade_total': ('quantidade', 'sum'),
            'num_pedidos_unicos': ('order_id', 'nunique'),
            'primeira_venda': ('data_transacao', 'min'),
            'ultima_venda': ('data_transacao', 'max'),
            # ATUALIZADO (Q1): Adiciona o valor unitário médio
            'valor_unitario_medio': ('valor_unitario', 'mean') 
        }
        agg_df = df.groupby(dimension_col).agg(**agg_ops).reset_index()

        # 2. Métricas Derivadas
        agg_df['ticket_medio'] = agg_df['receita_total'] / agg_df['num_pedidos_unicos']
        agg_df['qtd_media_por_pedido'] = agg_df['quantidade_total'] / agg_df['num_pedidos_unicos']
        
        dias_ativo = (agg_df['ultima_venda'] - agg_df['primeira_venda']).dt.days
        meses_ativo = (dias_ativo / 30.44).clip(lower=1)
        agg_df['frequencia_pedidos_mes'] = agg_df['num_pedidos_unicos'] / meses_ativo
        
        agg_df['recencia_dias'] = (self.today - agg_df['ultima_venda']).dt.days

        # 3. Cluster Vizu (Score Simples)
        agg_df['score_r'] = (1 - (agg_df['recencia_dias'] / agg_df['recencia_dias'].max())) * 100
        agg_df['score_f'] = (agg_df['frequencia_pedidos_mes'] / agg_df['frequencia_pedidos_mes'].max()) * 100
        agg_df['score_m'] = (agg_df['receita_total'] / agg_df['receita_total'].max()) * 100
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

    # ---
    # NÍVEL 1 (HOME) - (Sem mudanças, já está completo)
    # ---
    def get_home_metrics(self) -> dict:
        # ... (código da v1) ...
        logger.info(f"[MetricService] Calculando métricas Nível 1 para {self.client_id}")
        
        if self.df.empty:
            return {"scorecards": {}, "charts": []}

        scorecards_data = {
            "receita_total": float(self.df['valor_total_emitter'].sum()),
            "total_fornecedores": int(self.df['emitter_nome'].nunique()),
            "total_produtos": int(self.df['raw_product_description'].nunique()),
            "total_regioes": int(self.df['emitter_cidade'].nunique()),
            "total_clientes": int(self.df['receiver_nome'].nunique()),
            "total_pedidos": int(self.df['order_id'].nunique()),
        }

        receita_por_mes_df = self.df.groupby('ano_mes')['valor_total_emitter'].sum().sort_index()
        chart_data_receita_mes = [
            {"name": index, "receita": float(value)}
            for index, value in receita_por_mes_df.items()
        ]

        return {
            "scorecards": scorecards_data,
            "charts": [
                {
                    "id": "receita-por-mes",
                    "title": "Receita Total por Mês",
                    "data": chart_data_receita_mes
                }
            ]
        }

    # ---
    # NÍVEL 2 (MÓDULOS) - (Atualizado para Q2)
    # ---

    def get_fornecedores_overview(self) -> dict:
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Fornecedores) para {self.client_id}")
        
        # 1. Usa o Helper pré-calculado
        df_fornecedores_agg = self.df_fornecedores_agg

        # 2. Métricas Adicionais...
        df_fornecedores_tempo = self.df.sort_values('data_transacao').drop_duplicates('emitter_nome')
        df_fornecedores_tempo = df_fornecedores_tempo.groupby('ano_mes').size().cumsum().reset_index(name='total_cumulativo')
        
        df_top_produtos = self.df_produtos_agg.sort_values('receita_total', ascending=False).head(10)
        
        df_fornecedores_regiao = self.df.groupby('emitter_estado')['emitter_nome'].nunique().reset_index(name='contagem')

        # NOVO (Q2): Gráfico de Cohort (Tiers)
        df_cohort = df_fornecedores_agg.groupby('cluster_tier').size().reset_index(name='contagem')
        df_cohort['percentual'] = (df_cohort['contagem'] / df_cohort['contagem'].sum()) * 100
        # CORREÇÃO: Renomeia a coluna para corresponder ao schema ChartDataPoint
        df_cohort.rename(columns={'cluster_tier': 'name'}, inplace=True)

        return {
            "scorecard_total_fornecedores": int(df_fornecedores_agg.shape[0]),
            "chart_fornecedores_no_tempo": [{"name": r['ano_mes'], "total": r['total_cumulativo']} for r in df_fornecedores_tempo.to_dict('records')],
            "chart_fornecedores_por_regiao": [{"name": r['emitter_estado'], "total": r['contagem']} for r in df_fornecedores_regiao.to_dict('records')],
            "chart_cohort_fornecedores": df_cohort.to_dict('records'),
            "ranking_por_receita": df_fornecedores_agg.sort_values('receita_total', ascending=False).head(10).to_dict('records'),
            "ranking_por_ticket_medio": df_fornecedores_agg.sort_values('ticket_medio', ascending=False).head(10).to_dict('records'),
            # CORREÇÃO: Adiciona os rankings que faltavam no schema
            "ranking_por_qtd_media": df_fornecedores_agg.sort_values('qtd_media_por_pedido', ascending=False).head(10).to_dict('records'),
            "ranking_por_frequencia": df_fornecedores_agg.sort_values('frequencia_pedidos_mes', ascending=False).head(10).to_dict('records'),
            "ranking_produtos_mais_vendidos": df_top_produtos[['nome', 'receita_total', 'valor_unitario_medio']].to_dict('records'),
        }

    def get_clientes_overview(self) -> dict:
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Clientes) para {self.client_id}")
        
        # 1. Usa o Helper pré-calculado
        df_clientes_agg = self.df_clientes_agg
        
        # 2. Métricas Adicionais...
        df_clientes_regiao = self.df.groupby('receiver_estado')['receiver_nome'].nunique().reset_index(name='contagem')
        total_clientes_regiao = df_clientes_regiao['contagem'].sum()
        df_clientes_regiao['percentual'] = (df_clientes_regiao['contagem'] / total_clientes_regiao) * 100

        # NOVO (Q2): Gráfico de Cohort (Tiers)
        df_cohort = df_clientes_agg.groupby('cluster_tier').size().reset_index(name='contagem')
        df_cohort['percentual'] = (df_cohort['contagem'] / df_cohort['contagem'].sum()) * 100

        return {
            "scorecard_total_clientes": int(df_clientes_agg.shape[0]),
            "scorecard_ticket_medio_geral": float(df_clientes_agg['ticket_medio'].mean()),
            "scorecard_frequencia_media_geral": float(df_clientes_agg['frequencia_pedidos_mes'].mean()),
            "chart_clientes_por_regiao": [{"name": r['receiver_estado'], "percentual": r['percentual']} for r in df_clientes_regiao.to_dict('records')],
            "chart_cohort_clientes": df_cohort.to_dict('records'), # (Q2)
            "ranking_por_receita": df_clientes_agg.sort_values('receita_total', ascending=False).head(10).to_dict('records'),
            "ranking_por_ticket_medio": df_clientes_agg.sort_values('ticket_medio', ascending=False).head(10).to_dict('records'),
            "ranking_por_qtd_pedidos": df_clientes_agg.sort_values('num_pedidos_unicos', ascending=False).head(10).to_dict('records'),
            "ranking_por_cluster_vizu": df_clientes_agg.sort_values('cluster_score', ascending=False).head(10).to_dict('records'),
        }

    def get_produtos_overview(self) -> dict:
        logger.info(f"[MetricService] Calculando métricas Nível 2 (Produtos) para {self.client_id}")
        
        # 1. Usa o Helper pré-calculado
        df_produtos_agg = self.df_produtos_agg

        return {
            "scorecard_total_itens_unicos": int(df_produtos_agg.shape[0]),
            # ATUALIZADO (Q1): Rankings agora incluem valor unitário médio
            "ranking_por_receita": df_produtos_agg.sort_values('receita_total', ascending=False).head(10)[['nome', 'receita_total', 'valor_unitario_medio']].to_dict('records'),
            "ranking_por_volume": df_produtos_agg.sort_values('quantidade_total', ascending=False).head(10)[['nome', 'quantidade_total', 'valor_unitario_medio']].to_dict('records'),
            "ranking_por_ticket_medio": df_produtos_agg.sort_values('ticket_medio', ascending=False).head(10)[['nome', 'ticket_medio', 'valor_unitario_medio']].to_dict('records'),
        }

    def get_pedidos_overview(self) -> dict:
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
        return {
            "scorecard_ticket_medio_por_pedido": float(df_pedidos_agg['ticket_pedido'].mean()),
            "scorecard_qtd_media_produtos_por_pedido": float(df_pedidos_agg['qtd_produtos'].mean()),
            "scorecard_taxa_recorrencia_clientes_perc": taxa_recorrencia,
            "scorecard_recencia_media_entre_pedidos_dias": float(recencia_media_dias),
            "ranking_pedidos_por_regiao": self.df.groupby('emitter_cidade')['order_id'].nunique().nlargest(10).reset_index(name='contagem').to_dict('records'),
            "ultimos_pedidos": df_pedidos_agg.sort_values('data_transacao', ascending=False).head(20).to_dict('records')
        }

    # ---
    # NÍVEL 3 (DETALHE) - (Atualizado para Q3 e Q4)
    # ---

    def get_fornecedor_details(self, nome_fornecedor: str) -> dict:
        # ... (sem mudanças significativas, código da v1) ...
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Fornecedor: {nome_fornecedor}")
        df_filtrado = self.df[self.df['emitter_nome'] == nome_fornecedor].copy()
        if df_filtrado.empty:
            raise ValueError(f"Fornecedor não encontrado: {nome_fornecedor}")
        dados_cadastrais = df_filtrado.iloc[0][
            ['emitter_nome', 'emitter_cnpj', 'emitter_telefone', 'emitter_estado', 'emitter_cidade']
        ].to_dict()
        df_agg_clientes = self._get_aggregated_metrics_by_dimension(df_filtrado, 'receiver_nome')
        df_agg_produtos = self._get_aggregated_metrics_by_dimension(df_filtrado, 'raw_product_description')
        df_agg_regioes = self._get_aggregated_metrics_by_dimension(df_filtrado, 'receiver_cidade')
        return {
            "dados_cadastrais": dados_cadastrais,
            "rankings_internos": {
                "clientes_por_receita": df_agg_clientes.sort_values('receita_total', ascending=False).head(5).to_dict('records'),
                "produtos_por_receita": df_agg_produtos.sort_values('receita_total', ascending=False).head(5).to_dict('records'),
                "regioes_por_receita": df_agg_regioes.sort_values('receita_total', ascending=False).head(5).to_dict('records'),
            }
        }


    def get_cliente_details(self, nome_cliente: str) -> dict:
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Cliente: {nome_cliente}")
        
        df_filtrado = self.df[self.df['receiver_nome'] == nome_cliente].copy()
        if df_filtrado.empty:
            raise ValueError(f"Cliente não encontrado: {nome_cliente}")
            
        dados_cadastrais = df_filtrado.iloc[0][
            ['receiver_nome', 'receiver_cnpj', 'receiver_telefone', 'receiver_estado', 'receiver_cidade']
        ].to_dict()
        
        # ATUALIZADO (Q3): Pega o scorecard completo (freq, ticket, tier)
        # Filtramos o DataFrame pré-calculado
        scorecards = self.df_clientes_agg[self.df_clientes_agg['nome'] == nome_cliente].to_dict('records')
        
        df_agg_produtos = self._get_aggregated_metrics_by_dimension(df_filtrado, 'raw_product_description')

        df_ultimos_pedidos = df_filtrado.groupby('order_id').agg(
            data_transacao=('data_transacao', 'first'),
            valor_total=('valor_total_emitter', 'sum')
        ).sort_values('data_transacao', ascending=False).head(10)

        return {
            "dados_cadastrais": dados_cadastrais,
            "scorecards": scorecards[0] if scorecards else {}, # (Q3)
            "rankings_internos": {
                "mix_de_produtos_por_receita": df_agg_produtos.sort_values('receita_total', ascending=False).head(5)[['nome', 'receita_total', 'valor_unitario_medio']].to_dict('records'), # (Q1)
                "ultimos_pedidos": df_ultimos_pedidos.reset_index().to_dict('records')
            }
        }

    def get_produto_details(self, nome_produto: str) -> dict:
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Produto: {nome_produto}")
        
        df_filtrado = self.df[self.df['raw_product_description'] == nome_produto].copy()
        if df_filtrado.empty:
            raise ValueError(f"Produto não encontrado: {nome_produto}")

        # ATUALIZADO (Q4): Pega o scorecard completo (freq, ticket)
        scorecards = self.df_produtos_agg[self.df_produtos_agg['nome'] == nome_produto].to_dict('records')
        
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

        return {
            "nome_produto": nome_produto,
            "scorecards": scorecards[0] if scorecards else {}, # (Q4)
            "charts": {
                 "segmentos_de_clientes": df_cohort_produto.to_dict('records') # (Q4)
            },
            "rankings_internos": {
                "clientes_por_receita": df_agg_clientes.sort_values('receita_total', ascending=False).head(5).to_dict('records'),
                "regioes_por_receita": df_agg_regioes.sort_values('receita_total', ascending=False).head(5).to_dict('records'),
            }
        }
        
    def get_pedido_details(self, order_id: str) -> dict:
        # ... (sem mudanças significativas, código da v1) ...
        logger.info(f"[MetricService] Calculando métricas Nível 3 para Pedido: {order_id}")
        df_filtrado = self.df[self.df['order_id'] == order_id].copy()
        if df_filtrado.empty:
            raise ValueError(f"Pedido (order_id) não encontrado: {order_id}")
        dados_cliente = df_filtrado.iloc[0][
            ['receiver_nome', 'receiver_cnpj', 'receiver_telefone', 'receiver_estado', 'receiver_cidade']
        ].to_dict()
        itens_pedido = df_filtrado[
            ['raw_product_description', 'quantidade', 'valor_unitario', 'valor_total_emitter']
        ].to_dict('records')
        total_pedido = float(df_filtrado['valor_total_emitter'].sum())
        status_pedido = "Status Indisponível (OLTP)" # Dado OLTP (Fora do Escopo)
        return {
            "order_id": order_id,
            "status_pedido": status_pedido,
            "total_pedido": total_pedido,
            "dados_cliente": dados_cliente,
            "itens_pedido": itens_pedido
        }