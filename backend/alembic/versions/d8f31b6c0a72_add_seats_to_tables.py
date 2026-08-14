"""add seats to tables

Revision ID: d8f31b6c0a72
Revises: c2e7b41f8a90
Create Date: 2026-08-14 13:18:44.107233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f31b6c0a72'
down_revision: Union[str, None] = 'c2e7b41f8a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Quatre couverts par défaut : la table la plus courante en salle, et une
    # valeur que le manager corrigera d'un geste plutôt que de la saisir pour
    # chacune de ses tables.
    op.add_column('tables', sa.Column('seats', sa.Integer(), nullable=False, server_default='4'))


def downgrade() -> None:
    op.drop_column('tables', 'seats')
