"""add order modification requests

Revision ID: f620a92ca76a
Revises: cf9d95d06e07
Create Date: 2026-09-03 20:14:32.295967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f620a92ca76a'
down_revision: Union[str, None] = 'cf9d95d06e07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('order_modification_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'RESOLVED', name='modificationrequeststatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_modification_requests_order_id'), 'order_modification_requests', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_modification_requests_restaurant_id'), 'order_modification_requests', ['restaurant_id'], unique=False)
    op.create_table('order_modification_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('request_id', sa.Integer(), nullable=False),
    sa.Column('menu_item_id', sa.Integer(), nullable=False),
    sa.Column('menu_item_name', sa.String(length=120), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('previous_quantity', sa.Integer(), nullable=False),
    sa.Column('requested_quantity', sa.Integer(), nullable=False),
    sa.Column('notes', sa.String(length=300), nullable=True),
    sa.Column('is_shared', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'DECLINED', name='modificationlinestatus'), nullable=False),
    sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], ),
    sa.ForeignKeyConstraint(['request_id'], ['order_modification_requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_modification_lines_request_id'), 'order_modification_lines', ['request_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index(op.f('ix_order_modification_lines_request_id'), table_name='order_modification_lines')
    op.drop_table('order_modification_lines')
    op.drop_index(op.f('ix_order_modification_requests_restaurant_id'), table_name='order_modification_requests')
    op.drop_index(op.f('ix_order_modification_requests_order_id'), table_name='order_modification_requests')
    op.drop_table('order_modification_requests')
    # ### end Alembic commands ###
