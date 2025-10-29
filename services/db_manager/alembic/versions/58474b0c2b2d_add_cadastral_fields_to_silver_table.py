"""
add_cadastral_fields_and_align_schema (v2)

Revision ID: <ID_GERADO_PELO_ALEMBIC>
Revises: 841794fbbc8f
Create Date: <DATA_GERADA>
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<ID_GERADO_PELO_ALEMBIC>'  # Mantenha o ID que o Alembic gerou
down_revision = '841794fbbc8f'  # Aponta para a nossa migração anterior
branch_labels = None
depends_on = None

TABLE_NAME = 'pm_dados_faturamento_cliente_x'

def upgrade() -> None:
    # --- Passo 1: Adicionar as novas colunas que faltam ---
    
    # Emissor (Fornecedor)
    op.add_column(TABLE_NAME, sa.Column('emitter_cnpj', sa.String(), nullable=True))
    op.add_column(TABLE_NAME, sa.Column('emitter_telefone', sa.String(), nullable=True))
    
    # Receptor (Cliente)
    op.add_column(TABLE_NAME, sa.Column('receiver_cnpj', sa.String(), nullable=True))
    op.add_column(TABLE_NAME, sa.Column('receiver_telefone', sa.String(), nullable=True))
    op.add_column(TABLE_NAME, sa.Column('receiver_estado', sa.String(), nullable=True))

    # --- Passo 2: Renomear colunas existentes para bater com o schema_mapping ---
    
    # Renomeia 'emitter_estado_uf' -> 'emitter_estado'
    op.alter_column(
        TABLE_NAME,
        'emitter_estado_uf',
        new_column_name='emitter_estado',
        existing_type=sa.String()
    )


def downgrade() -> None:
    # --- Passo 1: Renomear de volta ---
    op.alter_column(
        TABLE_NAME,
        'emitter_estado',
        new_column_name='emitter_estado_uf',
        existing_type=sa.String()
    )
    
    # --- Passo 2: Remover as colunas novas ---
    op.drop_column(TABLE_NAME, 'receiver_estado')
    op.drop_column(TABLE_NAME, 'receiver_telefone')
    op.drop_column(TABLE_NAME, 'receiver_cnpj')
    
    op.drop_column(TABLE_NAME, 'emitter_telefone')
    op.drop_column(TABLE_NAME, 'emitter_cnpj')