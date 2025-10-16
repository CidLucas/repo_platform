"""Adiciona secret_manager_id a credencial_servico_externo

Revision ID: 46b6fbc92111
Revises: 1721df8bc2e1
Create Date: 2025-10-07 16:16:14.918975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # Importe os tipos corretos se necessário



# revision identifiers, used by Alembic.
revision: str = '46b6fbc92111'
down_revision: Union[str, Sequence[str], None] = '1721df8bc2e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'credencial_servico_externo', 
        sa.Column('secret_manager_id', sa.String, nullable=False, unique=True)
    )

def downgrade() -> None:
    op.drop_column('credencial_servico_externo', 'secret_manager_id')
