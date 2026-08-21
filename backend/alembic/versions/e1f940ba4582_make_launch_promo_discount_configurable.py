"""make launch promo discount configurable

Revision ID: e1f940ba4582
Revises: 0c0e37c86fe3
Create Date: 2026-08-21 08:35:47.555909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f940ba4582'
down_revision: Union[str, None] = '0c0e37c86fe3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table de config singleton — une seule ligne (id=1), insérée ici avec les
    # valeurs qui reproduisent exactement le lancement d'origine (2026-08-21,
    # 100 % pour 20 places) : changer la config plus tard est désormais
    # l'affaire de l'écran admin (platform_admin), jamais d'une migration.
    op.create_table(
        'launch_campaign_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('discount_percent', sa.Integer(), nullable=False),
        sa.Column('max_grants', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute("INSERT INTO launch_campaign_config (id, discount_percent, max_grants) VALUES (1, 100, 20)")

    op.add_column('restaurants', sa.Column('launch_promo_discount_percent', sa.Integer(), nullable=True))
    # Conserver l'historique : un restaurant déjà marqué comme bénéficiaire
    # (booléen `launch_promo_granted`, offre d'origine toujours à 100 %)
    # devient `100`, pas `NULL` — sinon on perdrait la trace de qui a
    # bénéficié de l'offre de lancement avant qu'elle ne devienne configurable.
    op.execute(
        "UPDATE restaurants SET launch_promo_discount_percent = 100 WHERE launch_promo_granted IS TRUE"
    )
    op.drop_column('restaurants', 'launch_promo_granted')


def downgrade() -> None:
    op.add_column(
        'restaurants',
        sa.Column('launch_promo_granted', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    )
    op.execute(
        "UPDATE restaurants SET launch_promo_granted = TRUE WHERE launch_promo_discount_percent IS NOT NULL"
    )
    op.drop_column('restaurants', 'launch_promo_discount_percent')
    op.drop_table('launch_campaign_config')
