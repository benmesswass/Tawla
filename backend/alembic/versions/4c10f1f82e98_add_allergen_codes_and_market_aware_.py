"""add allergen codes and market aware halal default

Revision ID: 4c10f1f82e98
Revises: 080e1bc60b7b
Create Date: 2026-09-04 10:40:56.420430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c10f1f82e98'
down_revision: Union[str, None] = '080e1bc60b7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `is_halal` change de défaut PYTHON (market-aware, voir models.py) mais
    # pas de type de colonne : rien à migrer pour lui. `allergen_codes` :
    # codes INCO séparés par une virgule, coexiste avec `allergens` (texte
    # libre, inchangé) — voir models.py::ALLERGEN_CODES.
    op.add_column('menu_items', sa.Column('allergen_codes', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('menu_items', 'allergen_codes')
