"""add paid_at to orders

Revision ID: cd13a009784f
Revises: a1c4e6f2b8d3
Create Date: 2026-08-31 12:46:39.553151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd13a009784f'
down_revision: Union[str, None] = 'a1c4e6f2b8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('orders', 'paid_at')
