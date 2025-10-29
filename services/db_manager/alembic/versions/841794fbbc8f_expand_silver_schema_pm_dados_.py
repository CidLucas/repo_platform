"""
expand_silver_schema_pm_dados_ (CORRIGIDO)

Esta é agora a migração inicial que cria a tabela
pm_dados_faturamento_cliente_x com o schema Prata completo.

Revision ID: 841794fbbc8f
Revises: 
Create Date: 2025-10-22 17:15:23.701193
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '841794fbbc8f'
down_revision = None  # Define esta como a primeira migração (raiz)
branch_labels = None
depends_on = None

TABLE_NAME = 'pm_dados_faturamento_cliente_x'

def upgrade() -> None:
    # Agora nós CRIAMOS a tabela do zero, já com o schema Prata final
    op.create_table(
        TABLE_NAME,
        # Colunas padrão Vizu (assumindo que você as queira)
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('data_atualizacao', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        
        # Coluna de data que já existia (mas agora é criada)
        sa.Column('data_transacao', sa.DateTime, nullable=True),

        # Colunas renomeadas (agora são criadas com o nome certo)
        sa.Column('receiver_nome', sa.String(), nullable=True), # Antiga 'id_cliente'
        sa.Column('valor_total_emitter', sa.Numeric(precision=10, scale=2), nullable=True), # Antiga 'valor_total'

        # Novas colunas
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('quantidade', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('valor_unitario', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('valor_total_receiver', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('emitter_nome', sa.String(), nullable=True),
        sa.Column('emitter_cidade', sa.String(), nullable=True),
        sa.Column('emitter_estado_uf', sa.String(), nullable=True),
        sa.Column('receiver_cidade', sa.String(), nullable=True),
        sa.Column('raw_product_description', sa.String(), nullable=True),
        sa.Column('raw_product_category', sa.String(), nullable=True),
        sa.Column('raw_ncm', sa.String(), nullable=True),
        sa.Column('raw_cfop', sa.String(), nullable=True)
    )
    # Adicionamos os índices
    op.create_index(op.f('ix_pm_dados_faturamento_cliente_x_order_id'), TABLE_NAME, ['order_id'], unique=False)
    op.create_index(op.f('ix_pm_dados_faturamento_cliente_x_data_transacao'), TABLE_NAME, ['data_transacao'], unique=False)


def downgrade() -> None:
    # O downgrade é simplesmente apagar a tabela inteira
    op.drop_index(op.f('ix_pm_dados_faturamento_cliente_x_order_id'), table_name=TABLE_NAME)
    op.drop_index(op.f('ix_pm_dados_faturamento_cliente_x_data_transacao'), table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)