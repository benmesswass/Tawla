"""add stripe customer and subscription id to restaurants

Revision ID: b6601f7cf556
Revises: abffd3e870b1
Create Date: 2026-09-02 11:05:04.155705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6601f7cf556'
down_revision: Union[str, None] = 'abffd3e870b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Abonnement récurrent Stripe pour l'abonnement Tawla elle-même (France,
    # MARCHE_FRANCE.md Phase F6 étape 4) — jamais Konnect (pas de récurrence
    # dans son API). En clair, pas chiffré : ni l'un ni l'autre n'est un
    # secret (voir models.py::Restaurant.stripe_customer_id).
    op.add_column('restaurants', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('restaurants', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('restaurants', 'stripe_subscription_id')
    op.drop_column('restaurants', 'stripe_customer_id')
