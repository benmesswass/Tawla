"""add stripe account id to restaurants

Revision ID: abffd3e870b1
Revises: 52d242d3bb0b
Create Date: 2026-09-01 17:46:28.540666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abffd3e870b1'
down_revision: Union[str, None] = '52d242d3bb0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Compte Connect Standard du restaurant (France, MARCHE_FRANCE.md Phase
    # F6 étape 3) — le restaurant est le marchand, jamais Tawla, même modèle
    # que konnect_wallet_id. En clair, pas chiffré : un account_id Connect
    # n'est pas un secret (voir models.py::Restaurant.stripe_account_id).
    # Nullable sans défaut : tant que l'onboarding n'a pas démarré, le
    # paiement carte reste en mode démo (dégradation gracieuse).
    op.add_column(
        'restaurants',
        sa.Column('stripe_account_id', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('restaurants', 'stripe_account_id')
