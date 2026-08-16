"""add preparation_started_at to orders

Revision ID: 0492cab1ec18
Revises: cc0f0456fb36
Create Date: 2026-08-15 22:37:59.200722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0492cab1ec18'
down_revision: Union[str, None] = 'cc0f0456fb36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable sans reprise des lignes existantes : une commande déjà passée
    # n'a jamais eu de début de préparation horodaté, et l'inventer fausserait
    # les temps de cuisine du premier pilote.
    op.add_column('orders', sa.Column('preparation_started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'preparation_started_at')
