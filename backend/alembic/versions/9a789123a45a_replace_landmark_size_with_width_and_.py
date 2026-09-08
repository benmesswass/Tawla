"""replace landmark size with width and height

Revision ID: 9a789123a45a
Revises: b3ca1938f3f5
Create Date: 2026-09-08 08:44:39.492010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9a789123a45a'
down_revision: Union[str, None] = 'b3ca1938f3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_NAME = "landmarksize"
_ENUM_VALUES = ("SMALL", "MEDIUM", "LARGE")


def upgrade() -> None:
    # Retour de Wassim (2026-09-08) : trois préréglages ne suffisaient pas —
    # il veut étirer le repère à la souris et former n'importe quel
    # rectangle. server_default : les repères déjà posés (palier medium,
    # PR #172) reçoivent un rectangle de départ plutôt qu'un état à moitié
    # rempli.
    op.add_column('plan_landmarks', sa.Column('width', sa.Float(), nullable=False, server_default='12'))
    op.add_column('plan_landmarks', sa.Column('height', sa.Float(), nullable=False, server_default='7'))
    op.drop_column('plan_landmarks', 'size')
    postgresql.ENUM(name=_ENUM_NAME).drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
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
    op.drop_column('plan_landmarks', 'height')
    op.drop_column('plan_landmarks', 'width')
