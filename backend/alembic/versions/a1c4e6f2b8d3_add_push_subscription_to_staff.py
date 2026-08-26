"""add push_subscription to staff

Revision ID: a1c4e6f2b8d3
Revises: 9322d4595cb0
Create Date: 2026-08-26 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e6f2b8d3'
down_revision: Union[str, None] = '9322d4595cb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'staff',
        sa.Column('push_subscription', sa.String(length=2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('staff', 'push_subscription')
