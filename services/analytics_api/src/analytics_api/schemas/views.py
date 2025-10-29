"""
Schemas Canônicos Vizu (Nível Prata)

Define os "Contratos de Dados" Pydantic que representam
as entidades de negócio de forma agnóstica.

O view_service (Bronze -> Silver) é responsável por transformar
os dados brutos do cliente (BigQuery, CSV, etc.) nestes formatos.

O metric_service (Silver -> Gold) consome estes formatos
para calcular KPIs, rankings e scorecards.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# ---
# VIEWS DE DIMENSÃO (Quem, O Quê, Onde)
# ---

class RegiaoView(BaseModel):
    """
    Dimensão Canônica: Região.
    Representa uma localização geográfica (ex: Região de Venda, Região do Cliente).
    """
    id_regiao: str = Field(description="ID único da região (ex: hash, nome normalizado, CEP)")
    cidade: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = None
    
    class Config:
        orm_mode = True # Permite fácil conversão de ORMs
        frozen = True   # Dimensões são imutáveis por definição


class ClienteView(BaseModel):
    """
    Dimensão Canônica: Cliente.
    Representa a entidade que COMPRA.
    - Para Fazenda Soledade: Um bar, restaurante.
    - Para Polen: Um comprador de lixo.
    """
    id_cliente: str = Field(description="ID único do cliente (ex: CNPJ, email, ID interno)")
    nome_cliente: str
    id_regiao: str = Field(description="Chave estrangeira para RegiaoView")
    data_cadastro: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        frozen = True


class VendedorView(BaseModel):
    """
    Dimensão Canônica: Vendedor.
    Representa a entidade que VENDE.
    - Para Fazenda Soledade: A própria Fazenda (haverá apenas 1).
    - Para Polen: A Cooperativa.
    """
    id_vendedor: str = Field(description="ID único do vendedor (ex: CNPJ, ID interno da cooperativa)")
    nome_vendedor: str
    id_regiao: str = Field(description="Chave estrangeira para RegiaoView")
    
    class Config:
        orm_mode = True
        frozen = True


class ProdutoView(BaseModel):
    """
    Dimensão Canônica: Produto.
    Representa o item sendo transacionado.
    - Para Fazenda Soledade: Cachaça Prata, Cachaça Ouro.
    - Para Polen: PET, Papelão, Vidro.
    """
    id_produto: str = Field(description="ID único do produto (ex: SKU)")
    nome_produto: str
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    
    class Config:
        orm_mode = True
        frozen = True


# ---
# VIEWS DE FATO (O Que Aconteceu, Quando)
# ---

class TransacaoView(BaseModel):
    """
    View de Fato: Transação (Substitui 'PedidoView' para ser mais agnóstico).
    Representa o evento principal: uma venda/transação.
    Esta é a tabela de fatos central que une as dimensões.
    """
    id_transacao: str = Field(description="ID único do evento (ex: ID do pedido, ID da nota fiscal)")
    data_transacao: datetime
    
    # Chaves das Dimensões
    id_cliente: str = Field(description="Chave para ClienteView (quem comprou)")
    id_vendedor: str = Field(description="Chave para VendedorView (quem vendeu)")
    id_produto: str = Field(description="Chave para ProdutoView (o que foi vendido)")
    
    # Métricas (Nível Prata)
    valor_total: float = Field(description="Métrica 'receita' desta transação")
    quantidade: int = Field(description="Métrica 'quantidade' nesta transação")
    preco_unitario: Optional[float] = None
    
    class Config:
        orm_mode = True


class EstoqueView(BaseModel):
    """
    View de Fato (Snapshot): Estoque.
    Representa um snapshot do inventário em um ponto no tempo.
    - Para Fazenda Soledade: Quantidade de cachaça disponível.
    - Para Polen: (Provavelmente não se aplica, a lista ficaria vazia).
    """
    id_produto: str = Field(description="Chave para ProdutoView")
    id_local_estoque: str = Field(description="Onde o estoque está (ex: id_vendedor)")
    quantidade_disponivel: int
    data_snapshot: datetime
    
    class Config:
        orm_mode = True