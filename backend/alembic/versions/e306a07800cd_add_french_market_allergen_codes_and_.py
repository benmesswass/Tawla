"""add french market allergen codes and dietary markers

Revision ID: e306a07800cd
Revises: d1fc407fddd7
Create Date: 2026-08-24 14:09:03.264867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e306a07800cd'
down_revision: Union[str, None] = 'd1fc407fddd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # F5-A6 (MARCHE_FRANCE.md) : allergènes structurés (14 catégories INCO,
    # règlement UE 1169/2011) + marqueurs végétarien/vegan/sans gluten.
    # Distinct de la colonne `allergens` existante (texte libre, conservée
    # telle quelle) — voir menu/models.py::MenuItem.
    #
    # server_default nécessaire pour les trois booléens : NOT NULL sur une
    # table qui a déjà des lignes. Faux pour les trois — une affirmation
    # "vegan"/"vegetarien"/"sans gluten" engage le restaurant, elle ne se
    # déduit jamais d'un article existant.
    op.add_column('menu_items', sa.Column('allergen_codes', sa.String(length=200), nullable=True))
    op.add_column(
        'menu_items', sa.Column('is_vegetarian', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column('menu_items', sa.Column('is_vegan', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        'menu_items', sa.Column('is_gluten_free', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column('menu_items', 'is_gluten_free')
    op.drop_column('menu_items', 'is_vegan')
    op.drop_column('menu_items', 'is_vegetarian')
    op.drop_column('menu_items', 'allergen_codes')
