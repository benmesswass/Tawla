"""add menu regimes

Revision ID: 9322d4595cb0
Revises: e12f2586aacc
Create Date: 2026-08-26 13:01:10.079439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9322d4595cb0'
down_revision: Union[str, None] = 'e12f2586aacc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'menu_regimes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('restaurant_id', 'name', name='uq_menu_regime_restaurant_name'),
    )
    op.create_index(op.f('ix_menu_regimes_restaurant_id'), 'menu_regimes', ['restaurant_id'], unique=False)

    # Association pure : ondelete=CASCADE des deux côtés, pour que Postgres
    # nettoie lui-même la ligne de liaison quand un article ou un régime est
    # supprimé, sans dépendre d'un cascade ORM (voir menu/models.py).
    op.create_table(
        'menu_item_regimes',
        sa.Column('menu_item_id', sa.Integer(), nullable=False),
        sa.Column('regime_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['regime_id'], ['menu_regimes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('menu_item_id', 'regime_id'),
    )


def downgrade() -> None:
    op.drop_table('menu_item_regimes')

    op.drop_index(op.f('ix_menu_regimes_restaurant_id'), table_name='menu_regimes')
    op.drop_table('menu_regimes')
