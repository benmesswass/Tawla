"""add shared_with to order items

Revision ID: 3cb610181782
Revises: 0492cab1ec18
Create Date: 2026-08-15 22:45:19.583959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cb610181782'
down_revision: Union[str, None] = '0492cab1ec18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, sans reprise : les commandes passées n'ont jamais porté cette
    # précision, et « partagé par toute la table » est justement ce que veut
    # dire l'absence de valeur.
    op.add_column('order_items', sa.Column('shared_with', sa.String(length=60), nullable=True))


def downgrade() -> None:
    op.drop_column('order_items', 'shared_with')
