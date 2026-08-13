"""add last_order_at to loyalty_members

Revision ID: f4a2c8d90b15
Revises: e3b9d5a71c48
Create Date: 2026-08-13 19:05:12.884301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a2c8d90b15'
down_revision: Union[str, None] = 'e3b9d5a71c48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable sans valeur par défaut : on ne connaît pas la date de dernière
    # commande des fiches existantes, et l'inventer fausserait la purge de
    # rétention. La purge retombe sur `created_at` quand la colonne est nulle.
    op.add_column(
        'loyalty_members',
        sa.Column('last_order_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('loyalty_members', 'last_order_at')
