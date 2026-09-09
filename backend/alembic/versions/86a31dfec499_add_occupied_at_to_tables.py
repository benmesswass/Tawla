"""add occupied_at to tables

Revision ID: 86a31dfec499
Revises: 50430d04a286
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86a31dfec499'
down_revision: Union[str, None] = '50430d04a286'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tables', sa.Column('occupied_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('tables', 'occupied_at')
