# src/analytics_api/schemas/metrics.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# ---
# SCHEMAS GENÉRICOS (Reutilizados)
# ---

class ChartDataPoint(BaseModel):
    """Um ponto de dados genérico para um gráfico (ex: Recharts)."""
    name: str  # Eixo X (ex: '2025-01', 'SP', 'Tier 1')
    
    # Permite qualquer outra métrica como Eixo Y
    class Config:
        extra = 'allow' # Permite 'receita', 'contagem', 'percentual', etc.

class ChartData(BaseModel):
    """Define a estrutura do JSON para um gráfico."""
    id: str  # ex: "receita-por-mes"
    title: str
    data: List[ChartDataPoint]

class RankingItem(BaseModel):
    """
    O schema de ranking agnóstico completo, produzido pelo helper.
    (Reflete o DataFrame de _get_aggregated_metrics_by_dimension)
    """
    nome: str = Field(description="Nome da dimensão (ex: nome do cliente, nome do produto)")
    receita_total: float
    quantidade_total: float
    num_pedidos_unicos: int
    primeira_venda: datetime
    ultima_venda: datetime
    ticket_medio: float
    qtd_media_por_pedido: float
    frequencia_pedidos_mes: float
    recencia_dias: int
    valor_unitario_medio: float = Field(description="Média do valor unitário (relevante para produtos)")
    cluster_score: float = Field(description="Score RFM (0-100) para clusterização")
    cluster_tier: str = Field(description="Segmento do cliente/fornecedor (ex: A, B, C, D)")

    class Config:
        orm_mode = True # Permite fácil conversão de DataFrames

class CadastralData(BaseModel):
    """Dados cadastrais (Dimensão) da camada Prata."""
    # Podem ser de Cliente ou Fornecedor
    emitter_nome: Optional[str] = None
    emitter_cnpj: Optional[str] = None
    emitter_telefone: Optional[str] = None
    emitter_estado: Optional[str] = None
    emitter_cidade: Optional[str] = None
    
    receiver_nome: Optional[str] = None
    receiver_cnpj: Optional[str] = None
    receiver_telefone: Optional[str] = None
    receiver_estado: Optional[str] = None
    receiver_cidade: Optional[str] = None
    
    class Config:
        extra = 'ignore' # Ignora campos extras se houver

# ---
# NÍVEL 1: HOME
# ---

class HomeScorecards(BaseModel):
    """Scorecards agregados para a Home."""
    receita_total: float
    total_fornecedores: int
    total_produtos: int
    total_regioes: int
    total_clientes: int
    total_pedidos: int

class HomeMetricsResponse(BaseModel):
    """Resposta completa para a Home (Nível 1)."""
    scorecards: HomeScorecards
    charts: List[ChartData]

# ---
# NÍVEL 2: MÓDULOS (OVERVIEW)
# ---

class FornecedoresOverviewResponse(BaseModel):
    scorecard_total_fornecedores: int
    chart_fornecedores_no_tempo: List[ChartDataPoint]
    chart_fornecedores_por_regiao: List[ChartDataPoint]
    chart_cohort_fornecedores: List[ChartDataPoint]
    ranking_por_receita: List[RankingItem]
    ranking_por_qtd_media: List[RankingItem]
    ranking_por_ticket_medio: List[RankingItem]
    ranking_por_frequencia: List[RankingItem]
    ranking_produtos_mais_vendidos: List[Dict[str, Any]] # (nome, receita_total, valor_unitario_medio)

class ClientesOverviewResponse(BaseModel):
    scorecard_total_clientes: int
    scorecard_ticket_medio_geral: float
    scorecard_frequencia_media_geral: float
    chart_clientes_por_regiao: List[ChartDataPoint]
    chart_cohort_clientes: List[ChartDataPoint]
    ranking_por_receita: List[RankingItem]
    ranking_por_ticket_medio: List[RankingItem]
    ranking_por_qtd_pedidos: List[RankingItem]
    ranking_por_cluster_vizu: List[RankingItem]

class ProdutosOverviewResponse(BaseModel):
    scorecard_total_itens_unicos: int
    ranking_por_receita: List[Dict[str, Any]] # (nome, receita_total, valor_unitario_medio)
    ranking_por_volume: List[Dict[str, Any]] # (nome, quantidade_total, valor_unitario_medio)
    ranking_por_ticket_medio: List[Dict[str, Any]] # (nome, ticket_medio, valor_unitario_medio)

class PedidoItem(BaseModel):
    order_id: str
    data_transacao: datetime
    id_cliente: str
    ticket_pedido: float
    qtd_produtos: int

class PedidosOverviewResponse(BaseModel):
    scorecard_ticket_medio_por_pedido: float
    scorecard_qtd_media_produtos_por_pedido: float
    scorecard_taxa_recorrencia_clientes_perc: float
    scorecard_recencia_media_entre_pedidos_dias: float
    ranking_pedidos_por_regiao: List[ChartDataPoint]
    ultimos_pedidos: List[PedidoItem]

# ---
# NÍVEL 3: DETALHE
# ---

class FornecedorDetailResponse(BaseModel):
    dados_cadastrais: CadastralData
    rankings_internos: Dict[str, List[RankingItem]]

class ClienteDetailResponse(BaseModel):
    dados_cadastrais: CadastralData
    scorecards: Optional[RankingItem] # O scorecard de um cliente é um RankingItem dele mesmo
    rankings_internos: Dict[str, List[RankingItem]]

class ProdutoDetailResponse(BaseModel):
    nome_produto: str
    scorecards: Optional[RankingItem]
    charts: Dict[str, List[ChartDataPoint]]
    rankings_internos: Dict[str, List[RankingItem]]

class PedidoItemDetalhe(BaseModel):
    raw_product_description: str
    quantidade: float
    valor_unitario: float
    valor_total_emitter: float
    
class PedidoDetailResponse(BaseModel):
    order_id: str
    status_pedido: str
    total_pedido: float
    dados_cliente: CadastralData
    itens_pedido: List[PedidoItemDetalhe]