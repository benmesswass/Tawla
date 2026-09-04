"""add vat category to menu and order items

Revision ID: 080e1bc60b7b
Revises: 27641fde1134
Create Date: 2026-09-04 09:52:49.727799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '080e1bc60b7b'
down_revision: Union[str, None] = '27641fde1134'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable des deux côtés : null = "sur_place" (voir menu/models.py,
    # orders/models.py). `order_items.vat_category` est une COPIE figée à la
    # commande (comme menu_item_name/unit_price), jamais relue depuis
    # menu_items après coup.
    op.add_column('menu_items', sa.Column('vat_category', sa.String(length=20), nullable=True))
    op.add_column('order_items', sa.Column('vat_category', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('order_items', 'vat_category')
    op.drop_column('menu_items', 'vat_category')
