"""add items_updated_at to orders

Revision ID: cf9d95d06e07
Revises: a3d844e17424
Create Date: 2026-09-03 13:42:13.264470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf9d95d06e07'
down_revision: Union[str, None] = 'a3d844e17424'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable sans valeur par défaut : aucune commande existante n'a été
    # éditée par son client, donc rien à y mettre de correct — le badge
    # "Modifiée" du pool serveur ne s'affiche que si la colonne est renseignée.
    op.add_column(
        'orders',
        sa.Column('items_updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('orders', 'items_updated_at')
