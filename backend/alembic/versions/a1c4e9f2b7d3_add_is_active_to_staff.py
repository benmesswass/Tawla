"""add is_active to staff

Revision ID: a1c4e9f2b7d3
Revises: 5b27b85b11ec
Create Date: 2026-08-13 09:12:07.441290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e9f2b7d3'
down_revision: Union[str, None] = '5b27b85b11ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default nécessaire : la colonne est NOT NULL et la table peut
    # déjà contenir des comptes — sans lui, l'ALTER TABLE échoue. Les comptes
    # existants sont donc tous actifs, ce qui est le comportement d'avant
    # cette colonne.
    op.add_column(
        'staff',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('staff', 'is_active')
