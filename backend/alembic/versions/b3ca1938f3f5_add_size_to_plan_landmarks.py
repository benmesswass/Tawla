"""add size to plan landmarks

Revision ID: b3ca1938f3f5
Revises: 55a307a3bc86
Create Date: 2026-09-08 07:50:51.868628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3ca1938f3f5'
down_revision: Union[str, None] = '55a307a3bc86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_NAME = "landmarksize"
_ENUM_VALUES = ("SMALL", "MEDIUM", "LARGE")


def upgrade() -> None:
    # Même piège que c2e7b41f8a90 (TableShape) : ALTER TABLE ADD COLUMN avec un
    # type Enum Postgres n'émet pas le CREATE TYPE automatiquement — il faut le
    # créer explicitement avant, avec create_type=False sur la colonne pour
    # éviter une double création. server_default sur la colonne NOT NULL : les
    # repères déjà posés en production n'ont pas de taille, MEDIUM comble le
    # vide sans état à moitié rempli.
    landmark_size_enum = postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME)
    landmark_size_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'plan_landmarks',
        sa.Column(
            'size',
            postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=False,
            server_default='MEDIUM',
        ),
    )


def downgrade() -> None:
    op.drop_column('plan_landmarks', 'size')
    postgresql.ENUM(name=_ENUM_NAME).drop(op.get_bind(), checkfirst=True)
