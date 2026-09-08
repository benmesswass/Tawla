"""move landmark geometry into parts

Revision ID: 50430d04a286
Revises: 9a789123a45a
Create Date: 2026-09-08 11:25:26.489299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50430d04a286'
down_revision: Union[str, None] = '9a789123a45a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Retour de Wassim (2026-09-08) : un rectangle étirable (PR #174) ne dit
    # pas un bar en L ni en U. La géométrie descend donc dans des tronçons —
    # le repère est leur union. Les repères déjà posés deviennent un tronçon
    # unique : même dessin qu'avant la migration, à l'identique.
    op.create_table(
        'plan_landmark_parts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('landmark_id', sa.Integer(), nullable=False),
        sa.Column('ordre', sa.Integer(), nullable=False),
        sa.Column('pos_x', sa.Float(), nullable=False),
        sa.Column('pos_y', sa.Float(), nullable=False),
        sa.Column('width', sa.Float(), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['landmark_id'], ['plan_landmarks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_plan_landmark_parts_landmark_id'), 'plan_landmark_parts', ['landmark_id'], unique=False
    )
    op.execute(
        "INSERT INTO plan_landmark_parts (landmark_id, ordre, pos_x, pos_y, width, height) "
        "SELECT id, 0, pos_x, pos_y, width, height FROM plan_landmarks"
    )
    op.drop_column('plan_landmarks', 'pos_x')
    op.drop_column('plan_landmarks', 'pos_y')
    op.drop_column('plan_landmarks', 'width')
    op.drop_column('plan_landmarks', 'height')


def downgrade() -> None:
    # Le rectangle revient : chaque repère reprend la **boîte englobante** de
    # ses tronçons, pas seulement le premier — un L rétrogradé doit rester à
    # l'endroit du L, pas se réduire à l'un de ses bras. server_default : un
    # repère sans tronçon (impossible via l'API, possible à la main) ne doit
    # pas faire échouer la migration.
    op.add_column('plan_landmarks', sa.Column('pos_x', sa.Float(), nullable=False, server_default='40'))
    op.add_column('plan_landmarks', sa.Column('pos_y', sa.Float(), nullable=False, server_default='14'))
    op.add_column('plan_landmarks', sa.Column('width', sa.Float(), nullable=False, server_default='12'))
    op.add_column('plan_landmarks', sa.Column('height', sa.Float(), nullable=False, server_default='7'))
    op.execute(
        "UPDATE plan_landmarks SET "
        "pos_x = (SELECT MIN(pos_x) FROM plan_landmark_parts WHERE landmark_id = plan_landmarks.id), "
        "pos_y = (SELECT MIN(pos_y) FROM plan_landmark_parts WHERE landmark_id = plan_landmarks.id), "
        "width = (SELECT MAX(pos_x + width) - MIN(pos_x) FROM plan_landmark_parts "
        "         WHERE landmark_id = plan_landmarks.id), "
        "height = (SELECT MAX(pos_y + height) - MIN(pos_y) FROM plan_landmark_parts "
        "          WHERE landmark_id = plan_landmarks.id) "
        "WHERE EXISTS (SELECT 1 FROM plan_landmark_parts WHERE landmark_id = plan_landmarks.id)"
    )
    op.drop_index(op.f('ix_plan_landmark_parts_landmark_id'), table_name='plan_landmark_parts')
    op.drop_table('plan_landmark_parts')
