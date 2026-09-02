"""add subscription cancel at period end to restaurants

Revision ID: 0b94aba76718
Revises: b6601f7cf556
Create Date: 2026-09-02 11:54:09.616764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b94aba76718'
down_revision: Union[str, None] = 'b6601f7cf556'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Annulation demandée par le manager depuis le portail Stripe (mode
    # Netflix, France) — voir models.py::Restaurant.subscription_cancel_at_period_end.
    op.add_column(
        'restaurants',
        sa.Column('subscription_cancel_at_period_end', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('restaurants', 'subscription_cancel_at_period_end')
