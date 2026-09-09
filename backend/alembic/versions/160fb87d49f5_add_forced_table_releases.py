"""add forced_table_releases

Revision ID: 160fb87d49f5
Revises: 86a31dfec499
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '160fb87d49f5'
down_revision: Union[str, None] = '86a31dfec499'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'forced_table_releases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=False),
        sa.Column('released_by_staff_id', sa.Integer(), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('order_status_snapshot', sa.String(length=40), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id']),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id']),
        sa.ForeignKeyConstraint(['released_by_staff_id'], ['staff.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_forced_table_releases_restaurant_id'), 'forced_table_releases', ['restaurant_id'], unique=False
    )
    op.create_index(
        op.f('ix_forced_table_releases_table_id'), 'forced_table_releases', ['table_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_forced_table_releases_table_id'), table_name='forced_table_releases')
    op.drop_index(op.f('ix_forced_table_releases_restaurant_id'), table_name='forced_table_releases')
    op.drop_table('forced_table_releases')
