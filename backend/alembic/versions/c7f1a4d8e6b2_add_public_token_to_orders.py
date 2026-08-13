"""add public_token to orders

Revision ID: c7f1a4d8e6b2
Revises: a1c4e9f2b7d3
Create Date: 2026-08-13 11:38:52.117904

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f1a4d8e6b2'
down_revision: Union[str, None] = 'a1c4e9f2b7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Colonne ajoutée en nullable, remplie ligne par ligne, puis passée en
    # NOT NULL : un server_default unique est impossible ici, chaque commande
    # doit recevoir SON propre token (une valeur partagée ne prouverait rien).
    op.add_column('orders', sa.Column('public_token', sa.String(length=64), nullable=True))

    orders = sa.table('orders', sa.column('id', sa.Integer), sa.column('public_token', sa.String))
    connection = op.get_bind()
    for (order_id,) in connection.execute(sa.select(orders.c.id)):
        connection.execute(
            orders.update().where(orders.c.id == order_id).values(public_token=secrets.token_urlsafe(32))
        )

    op.alter_column('orders', 'public_token', nullable=False)
    op.create_index('ix_orders_public_token', 'orders', ['public_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_orders_public_token', table_name='orders')
    op.drop_column('orders', 'public_token')
