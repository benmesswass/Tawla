"""add menu item photo storage

Revision ID: 12f7509d48c3
Revises: 3cb610181782
Create Date: 2026-08-16 11:40:59.605406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12f7509d48c3'
down_revision: Union[str, None] = '3cb610181782'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # La photo vit en base (bytea côté Postgres) et non sur le disque du
    # conteneur, éphémère chez Railway comme chez Render : sur disque, toute la
    # carte perdrait ses images au premier redéploiement.
    op.add_column('menu_items', sa.Column('image_data', sa.LargeBinary(), nullable=True))
    op.add_column('menu_items', sa.Column('image_content_type', sa.String(length=60), nullable=True))


def downgrade() -> None:
    # Les photos déposées sont perdues en redescendant : elles n'existent nulle
    # part ailleurs. `image_url` survit, et redevient ce qu'il était avant —
    # une adresse externe saisie à la main.
    op.drop_column('menu_items', 'image_content_type')
    op.drop_column('menu_items', 'image_data')
