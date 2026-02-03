# src/analytics_api/schemas/metrics.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

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
    data: list[ChartDataPoint]

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
    emitter_nome: str | None = None
    emitter_cnpj: str | None = None
    emitter_telefone: str | None = None
    emitter_estado: str | None = None
    emitter_cidade: str | None = None

    receiver_nome: str | None = None
    receiver_cnpj: str | None = None
    receiver_telefone: str | None = None
    receiver_estado: str | None = None
    receiver_cidade: str | None = None

    class Config:
        extra = 'ignore' # Ignora campos extras se houver

# ---
# SCHEMAS ESPECÍFICOS PARA RANKINGS DE PRODUTOS
# (Substitui dict[str, Any] por modelos explícitos)
# ---

class ProdutoRankingReceita(BaseModel):
    """Ranking simplificado de produtos por receita total."""
    nome: str = Field(description="Nome do produto")
    receita_total: float = Field(description="Receita total gerada pelo produto")
    valor_unitario_medio: float = Field(description="Valor unitário médio do produto")
    quantidade_total: float = Field(default=0, description="Quantidade total vendida")
    cluster_tier: str = Field(default="", description="Tier de classificação do produto (A, B, C, D)")

class ProdutoRankingVolume(BaseModel):
    """Ranking simplificado de produtos por volume (quantidade vendida)."""
    nome: str = Field(description="Nome do produto")
    quantidade_total: float = Field(description="Quantidade total vendida")
    valor_unitario_medio: float = Field(description="Valor unitário médio do produto")
    receita_total: float = Field(default=0, description="Receita total gerada pelo produto")
    cluster_tier: str = Field(default="", description="Tier de classificação do produto (A, B, C, D)")

class ProdutoRankingTicket(BaseModel):
    """Ranking simplificado de produtos por ticket médio."""
    nome: str = Field(description="Nome do produto")
    ticket_medio: float = Field(description="Ticket médio do produto")
    valor_unitario_medio: float = Field(description="Valor unitário médio do produto")
    quantidade_total: float = Field(default=0, description="Quantidade total vendida")
    cluster_tier: str = Field(default="", description="Tier de classificação do produto (A, B, C, D)")

# ---
# NÍVEL 1: HOME
# ---

class HomeScorecards(BaseModel):
    """Scorecards agregados para a Home."""
    receita_total: float
    total_fornecedores: int
    total_produtos: int
    total_clientes: int
    total_pedidos: int
    ticket_medio: float = 0.0
    crescimento_receita: float = 0.0
    total_regioes: int = 0  # Optional, computed from customer locations


class HomeMetricsResponse(BaseModel):
    """Resposta completa para a Home (Nível 1)."""
    scorecards: HomeScorecards
    chart_receita_no_tempo: list[ChartDataPoint] = []
    chart_pedidos_no_tempo: list[ChartDataPoint] = []
    ranking_clientes: list[RankingItem] = []
    ranking_fornecedores: list[RankingItem] = []
    ranking_produtos: list[ProdutoRankingReceita] = []

# ---
# NÍVEL 2: MÓDULOS (OVERVIEW)
# ---

class FornecedoresOverviewResponse(BaseModel):
    scorecard_total_fornecedores: int
    scorecard_crescimento_percentual: float | None = None  # Percentual de crescimento da base de fornecedores
    chart_fornecedores_no_tempo: list[ChartDataPoint]
    chart_receita_no_tempo: list[ChartDataPoint]  # Monthly revenue fluctuation
    chart_ticketmedio_no_tempo: list[ChartDataPoint]  # Monthly avg ticket fluctuation
    chart_quantidade_no_tempo: list[ChartDataPoint]  # Monthly volume (kg/tons) fluctuation
    chart_fornecedores_por_regiao: list[ChartDataPoint]
    chart_cohort_fornecedores: list[ChartDataPoint]
    ranking_por_receita: list[RankingItem]
    ranking_por_qtd_media: list[RankingItem]
    ranking_por_ticket_medio: list[RankingItem]
    ranking_por_frequencia: list[RankingItem]
    ranking_produtos_mais_vendidos: list[ProdutoRankingReceita]

class ClientesOverviewResponse(BaseModel):
    scorecard_total_clientes: int
    scorecard_ticket_medio_geral: float
    scorecard_frequencia_media_geral: float
    scorecard_crescimento_percentual: float | None = None  # Percentual de crescimento da base de clientes
    chart_clientes_no_tempo: list[ChartDataPoint]  # Time series (monthly unique customers)
    chart_receita_no_tempo: list[ChartDataPoint]  # Monthly revenue from customers
    chart_ticketmedio_no_tempo: list[ChartDataPoint]  # Monthly avg ticket from customers
    chart_quantidade_no_tempo: list[ChartDataPoint]  # Monthly volume purchased by customers
    chart_clientes_por_regiao: list[ChartDataPoint]
    chart_cohort_clientes: list[ChartDataPoint]
    ranking_por_receita: list[RankingItem]
    ranking_por_ticket_medio: list[RankingItem]
    ranking_por_qtd_pedidos: list[RankingItem]
    ranking_por_cluster_vizu: list[RankingItem]

class ProdutosOverviewResponse(BaseModel):
    scorecard_total_itens_unicos: int
    chart_produtos_no_tempo: list[ChartDataPoint]  # Time series (monthly unique products)
    chart_receita_no_tempo: list[ChartDataPoint]  # Monthly revenue from products
    chart_quantidade_no_tempo: list[ChartDataPoint]  # Monthly volume of products sold
    ranking_por_receita: list[ProdutoRankingReceita]
    ranking_por_volume: list[ProdutoRankingVolume]
    ranking_por_ticket_medio: list[ProdutoRankingTicket]

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
    chart_pedidos_no_tempo: list[ChartDataPoint]  # Time series (monthly unique orders)
    ranking_pedidos_por_regiao: list[ChartDataPoint]
    ultimos_pedidos: list[PedidoItem]

# ---
# NÍVEL 3: DETALHE
# ---

class FornecedorDetailResponse(BaseModel):
    dados_cadastrais: CadastralData
    rankings_internos: dict[str, list[RankingItem]]
    charts: dict[str, list[ChartDataPoint]] = {}  # Time series charts for this supplier

class ClienteDetailResponse(BaseModel):
    dados_cadastrais: CadastralData
    scorecards: RankingItem | None # O scorecard de um cliente é um RankingItem dele mesmo
    rankings_internos: dict[str, list[RankingItem]]

class ProdutoDetailResponse(BaseModel):
    nome_produto: str
    scorecards: RankingItem | None
    charts: dict[str, list[ChartDataPoint]]
    rankings_internos: dict[str, list[RankingItem]]

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
    itens_pedido: list[PedidoItemDetalhe]
