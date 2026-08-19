"""add subscription payment fields to restaurants

Revision ID: a4d92e6c1f08
Revises: 12f7509d48c3
Create Date: 2026-08-18 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a4d92e6c1f08'
down_revision: Union[str, None] = '12f7509d48c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Même type Postgres que celui créé par 5b27b85b11ec pour subscription_tier —
# create_type=False partout ici : il existe déjà, le recréer ferait échouer
# la migration (type déjà présent).
_ENUM_NAME = "subscriptiontier"
_ENUM_VALUES = ("ESSENTIEL", "PRO", "BUSINESS")


def upgrade() -> None:
    # Toutes nullables sans défaut : un établissement existant (pilote géré à
    # la main par setup_restaurant.py) n'a jamais payé en ligne — ces colonnes
    # doivent rester vides pour lui, pas prendre une valeur inventée.
    op.add_column(
        'restaurants',
        sa.Column('subscription_period_end', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'restaurants',
        sa.Column('subscription_payment_ref', sa.String(120), nullable=True),
    )
    op.add_column(
        'restaurants',
        sa.Column(
            'subscription_pending_tier',
            postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('restaurants', 'subscription_pending_tier')
    op.drop_column('restaurants', 'subscription_payment_ref')
    op.drop_column('restaurants', 'subscription_period_end')
