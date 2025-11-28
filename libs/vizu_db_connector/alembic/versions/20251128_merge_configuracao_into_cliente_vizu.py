"""merge_configuracao_into_cliente_vizu
Revision ID: 20251128_merge_configuracao_into_cliente_vizu
Revises: 20251126_add_server_defaults
Create Date: 2025-11-28

Add configuracao_negocio fields to cliente_vizu and copy existing data.
This is a safe first-step migration: it adds columns and copies data but does
not drop the legacy `configuracao_negocio` table. A follow-up migration should
remove the legacy table after the application has been updated.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251128_merge_configuracao_into_cliente_vizu'
down_revision = '20251126_add_server_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to cliente_vizu
    op.add_column('cliente_vizu', sa.Column('horario_funcionamento', postgresql.JSONB(), nullable=True))
    op.add_column('cliente_vizu', sa.Column('prompt_base', sa.Text(), nullable=True))
    op.add_column('cliente_vizu', sa.Column('ferramenta_rag_habilitada', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('cliente_vizu', sa.Column('ferramenta_sql_habilitada', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('cliente_vizu', sa.Column('ferramenta_agendamento_habilitada', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('cliente_vizu', sa.Column('collection_rag', sa.Text(), nullable=True))

    # Copy existing data from configuracao_negocio (if present)
    op.execute("""
    UPDATE cliente_vizu
    SET horario_funcionamento = cn.horario_funcionamento,
        prompt_base = cn.prompt_base,
        ferramenta_rag_habilitada = cn.ferramenta_rag_habilitada,
        ferramenta_sql_habilitada = cn.ferramenta_sql_habilitada,
        ferramenta_agendamento_habilitada = cn.ferramenta_agendamento_habilitada,
        collection_rag = NULL
    FROM configuracao_negocio cn
    WHERE cn.cliente_vizu_id = cliente_vizu.id;
    """)


def downgrade() -> None:
    # Remove added columns
    op.drop_column('cliente_vizu', 'collection_rag')
    op.drop_column('cliente_vizu', 'ferramenta_agendamento_habilitada')
    op.drop_column('cliente_vizu', 'ferramenta_sql_habilitada')
    op.drop_column('cliente_vizu', 'ferramenta_rag_habilitada')
    op.drop_column('cliente_vizu', 'prompt_base')
    op.drop_column('cliente_vizu', 'horario_funcionamento')
