"""Établissements de démonstration jetables

Marque les restaurants créés par POST /api/v1/demo/sessions et leur échéance
de suppression. Voir app/modules/demo/service.py.

Revision ID: d1fc407fddd7
Revises: a95edb7a2d12
Create Date: 2026-08-23 16:39:34.344557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1fc407fddd7'
down_revision: Union[str, None] = 'a95edb7a2d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default nécessaire : la colonne est NOT NULL et la table a déjà
    # des lignes en production — sans lui, `ALTER TABLE` échoue au démarrage
    # du conteneur. Conservé ensuite plutôt que retiré : SQLite ne sait pas
    # faire `ALTER COLUMN ... DROP DEFAULT`, et les migrations sont rejouées
    # sur SQLite par tests/test_migrations.py. Même choix que la migration
    # 2976b3bc4f38 qui a ajouté `restaurants.is_active`.
    op.add_column(
        'restaurants',
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('restaurants', sa.Column('demo_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_restaurants_is_demo'), 'restaurants', ['is_demo'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_restaurants_is_demo'), table_name='restaurants')
    op.drop_column('restaurants', 'demo_expires_at')
    op.drop_column('restaurants', 'is_demo')
