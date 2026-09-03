"""add legal info to restaurants

Revision ID: b7d3f19a6c42
Revises: a3d844e17424
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3f19a6c42'
down_revision: Union[str, None] = 'a3d844e17424'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Toutes nullables : mentions légales affichées sur la facture PDF si
    # renseignées (voir app/core/invoice.py), jamais exigées à l'inscription.
    op.add_column('restaurants', sa.Column('legal_address', sa.String(length=300), nullable=True))
    op.add_column('restaurants', sa.Column('tax_id', sa.String(length=60), nullable=True))
    op.add_column('restaurants', sa.Column('vat_number', sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column('restaurants', 'vat_number')
    op.drop_column('restaurants', 'tax_id')
    op.drop_column('restaurants', 'legal_address')
