"""add subscription downgrade pending tier to restaurants

Revision ID: bc842fe4de85
Revises: 0b94aba76718
Create Date: 2026-09-02 13:18:26.436994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bc842fe4de85'
down_revision: Union[str, None] = '0b94aba76718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Même type Postgres que celui créé par 5b27b85b11ec pour subscription_tier —
# create_type=False : il existe déjà, le recréer ferait échouer la migration.
_ENUM_NAME = "subscriptiontier"
_ENUM_VALUES = ("ESSENTIEL", "PRO", "BUSINESS")


def upgrade() -> None:
    # Rétrogradation programmée (France, Stripe, mode Netflix) — voir
    # models.py::Restaurant.subscription_downgrade_pending_tier.
    op.add_column(
        'restaurants',
        sa.Column(
            'subscription_downgrade_pending_tier',
            postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('restaurants', 'subscription_downgrade_pending_tier')
