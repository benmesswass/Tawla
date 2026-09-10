"""add added_by_name to order_items

Revision ID: a7e2f9c14b6d
Revises: 50430d04a286
Create Date: 2026-09-09 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7e2f9c14b6d'
down_revision: Union[str, None] = '50430d04a286'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Prénom de qui a ajouté le plat (identité de table, ROADMAP.md
    # §Override) — nullable : NULL pour toute commande déjà en base.
    op.add_column('order_items', sa.Column('added_by_name', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('order_items', 'added_by_name')
