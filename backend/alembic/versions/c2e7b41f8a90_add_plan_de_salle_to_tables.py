"""add plan de salle to tables

Revision ID: c2e7b41f8a90
Revises: f4a2c8d90b15
Create Date: 2026-08-14 11:42:18.330512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e7b41f8a90'
down_revision: Union[str, None] = 'f4a2c8d90b15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Position nullable et sans valeur par défaut : une table existante n'a pas
    # de place sur le plan tant que le manager ne l'y a pas posée. La placer
    # d'office en (0,0) empilerait toutes les tables dans un coin.
    op.add_column('tables', sa.Column('pos_x', sa.Float(), nullable=True))
    op.add_column('tables', sa.Column('pos_y', sa.Float(), nullable=True))
    op.add_column(
        'tables',
        sa.Column(
            'shape',
            sa.Enum('ROUND', 'SQUARE', 'RECT', name='tableshape'),
            nullable=False,
            server_default='ROUND',
        ),
    )


def downgrade() -> None:
    op.drop_column('tables', 'shape')
    op.drop_column('tables', 'pos_y')
    op.drop_column('tables', 'pos_x')
