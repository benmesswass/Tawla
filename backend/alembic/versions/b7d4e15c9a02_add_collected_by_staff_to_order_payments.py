"""add collected_by_staff_id to order_payments

Revision ID: b7d4e15c9a02
Revises: d64562dcc42c
Create Date: 2026-09-10 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b7d4e15c9a02'
down_revision: Union[str, None] = 'd64562dcc42c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, et rétro-remplie par personne : les parts déjà encaissées
    # avant cette colonne n'ont pas de réponse à « qui a encaissé », et
    # inventer un nom serait pire que de ne rien afficher.
    with op.batch_alter_table("order_payments") as batch_op:
        batch_op.add_column(sa.Column('collected_by_staff_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_order_payments_collected_by_staff_id', 'staff', ['collected_by_staff_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table("order_payments") as batch_op:
        batch_op.drop_constraint('fk_order_payments_collected_by_staff_id', type_='foreignkey')
        batch_op.drop_column('collected_by_staff_id')
