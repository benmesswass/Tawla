"""add plan de salle to tables

Revision ID: c2e7b41f8a90
Revises: f4a2c8d90b15
Create Date: 2026-08-14 11:42:18.330512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c2e7b41f8a90'
down_revision: Union[str, None] = 'f4a2c8d90b15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_NAME = "tableshape"
_ENUM_VALUES = ("ROUND", "SQUARE", "RECT")


def upgrade() -> None:
    # Position nullable et sans valeur par défaut : une table existante n'a pas
    # de place sur le plan tant que le manager ne l'y a pas posée. La placer
    # d'office en (0,0) empilerait toutes les tables dans un coin.
    op.add_column('tables', sa.Column('pos_x', sa.Float(), nullable=True))
    op.add_column('tables', sa.Column('pos_y', sa.Float(), nullable=True))

    # ALTER TABLE ADD COLUMN avec un type Enum Postgres n'émet pas le
    # CREATE TYPE automatiquement (contrairement à CREATE TABLE) — il faut le
    # créer explicitement avant, avec create_type=False sur la colonne pour
    # éviter une double création (même piège déjà résolu dans la migration
    # 5b27b85b11ec pour subscription_tier).
    table_shape_enum = postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME)
    table_shape_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'tables',
        sa.Column(
            'shape',
            postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=False,
            server_default='ROUND',
        ),
    )


def downgrade() -> None:
    op.drop_column('tables', 'shape')
    op.drop_column('tables', 'pos_y')
    op.drop_column('tables', 'pos_x')
    postgresql.ENUM(name=_ENUM_NAME).drop(op.get_bind(), checkfirst=True)
