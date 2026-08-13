"""add menu suggestions and order item origin

Revision ID: e3b9d5a71c48
Revises: c7f1a4d8e6b2
Create Date: 2026-08-13 14:22:18.903471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b9d5a71c48'
down_revision: Union[str, None] = 'c7f1a4d8e6b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'menu_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('menu_item_id', sa.Integer(), nullable=False),
        sa.Column('suggested_item_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id']),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id']),
        sa.ForeignKeyConstraint(['suggested_item_id'], ['menu_items.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('menu_item_id', 'suggested_item_id', name='uq_menu_suggestion_pair'),
    )
    op.create_index(
        op.f('ix_menu_suggestions_restaurant_id'), 'menu_suggestions', ['restaurant_id'], unique=False
    )
    op.create_index(
        op.f('ix_menu_suggestions_menu_item_id'), 'menu_suggestions', ['menu_item_id'], unique=False
    )

    # server_default nécessaire : colonne NOT NULL sur une table qui contient
    # déjà des lignes. Les commandes antérieures sont donc marquées « pas depuis
    # une suggestion », ce qui est exact — la fonctionnalité n'existait pas.
    op.add_column(
        'order_items',
        sa.Column('from_suggestion', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('order_items', 'from_suggestion')
    op.drop_index(op.f('ix_menu_suggestions_menu_item_id'), table_name='menu_suggestions')
    op.drop_index(op.f('ix_menu_suggestions_restaurant_id'), table_name='menu_suggestions')
    op.drop_table('menu_suggestions')
