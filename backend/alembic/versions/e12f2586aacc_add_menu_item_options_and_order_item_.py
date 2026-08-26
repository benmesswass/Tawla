"""add menu item options and order item options

Revision ID: e12f2586aacc
Revises: d1fc407fddd7
Create Date: 2026-08-26 09:41:00.672498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e12f2586aacc'
down_revision: Union[str, None] = 'd1fc407fddd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'menu_item_option_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('menu_item_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('min_select', sa.Integer(), nullable=False),
        sa.Column('max_select', sa.Integer(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id']),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_menu_item_option_groups_menu_item_id'), 'menu_item_option_groups', ['menu_item_id'], unique=False
    )
    op.create_index(
        op.f('ix_menu_item_option_groups_restaurant_id'), 'menu_item_option_groups', ['restaurant_id'], unique=False
    )

    op.create_table(
        'menu_item_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('price_delta', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['menu_item_option_groups.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_menu_item_options_group_id'), 'menu_item_options', ['group_id'], unique=False)

    # Choix figé au moment de la commande — jamais relu depuis
    # menu_item_options, qui peut changer ou disparaître après coup (voir
    # OrderItemOption dans orders/models.py).
    op.create_table(
        'order_item_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_item_id', sa.Integer(), nullable=False),
        sa.Column('group_name', sa.String(length=60), nullable=False),
        sa.Column('option_name', sa.String(length=60), nullable=False),
        sa.Column('price_delta', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_order_item_options_order_item_id'), 'order_item_options', ['order_item_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_order_item_options_order_item_id'), table_name='order_item_options')
    op.drop_table('order_item_options')

    op.drop_index(op.f('ix_menu_item_options_group_id'), table_name='menu_item_options')
    op.drop_table('menu_item_options')

    op.drop_index(op.f('ix_menu_item_option_groups_restaurant_id'), table_name='menu_item_option_groups')
    op.drop_index(op.f('ix_menu_item_option_groups_menu_item_id'), table_name='menu_item_option_groups')
    op.drop_table('menu_item_option_groups')
