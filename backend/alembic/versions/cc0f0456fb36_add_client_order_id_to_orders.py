"""add client_order_id to orders

Revision ID: cc0f0456fb36
Revises: d8f31b6c0a72
Create Date: 2026-08-15 19:18:50.499393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc0f0456fb36'
down_revision: Union[str, None] = 'd8f31b6c0a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('client_order_id', sa.String(length=64), nullable=True))

    # batch_alter_table : SQLite ne sait pas ajouter une contrainte à une table
    # existante. Sur Postgres (la cible réelle) ça émet l'ALTER TABLE habituel,
    # mais ça garde la chaîne rejouable en local — c'est ce qui permet à
    # tests/test_migrations.py de vérifier que le schéma suit les modèles.
    with op.batch_alter_table('orders') as batch:
        batch.create_unique_constraint('uq_orders_table_client_order', ['table_id', 'client_order_id'])


def downgrade() -> None:
    with op.batch_alter_table('orders') as batch:
        batch.drop_constraint('uq_orders_table_client_order', type_='unique')
    op.drop_column('orders', 'client_order_id')
