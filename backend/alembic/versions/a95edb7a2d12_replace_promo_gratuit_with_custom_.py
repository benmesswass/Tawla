"""replace promo_gratuit with custom promo fields

Revision ID: a95edb7a2d12
Revises: e1f940ba4582
Create Date: 2026-08-21 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a95edb7a2d12'
down_revision: Union[str, None] = 'e1f940ba4582'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `promo_gratuit` (booléen, jamais d'échéance) remplacé par une promo
    # personnalisée réduction + fenêtre de validité, réglable par restaurant
    # depuis l'écran admin (2026-08-21bis, voir Restaurant.custom_promo_*) —
    # aucun restaurant n'a de dérogation en cours au moment de cette
    # migration (posée à la main au cas par cas), rien à reporter.
    op.add_column('restaurants', sa.Column('custom_promo_discount_percent', sa.Integer(), nullable=True))
    op.add_column('restaurants', sa.Column('custom_promo_ends_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_column('restaurants', 'promo_gratuit')


def downgrade() -> None:
    op.add_column(
        'restaurants',
        sa.Column('promo_gratuit', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_column('restaurants', 'custom_promo_ends_at')
    op.drop_column('restaurants', 'custom_promo_discount_percent')
