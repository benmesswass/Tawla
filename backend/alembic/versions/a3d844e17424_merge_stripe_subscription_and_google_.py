"""merge stripe subscription and google review url branches

Revision ID: a3d844e17424
Revises: bc842fe4de85, a75721b32c6e
Create Date: 2026-09-02 13:52:46.859614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d844e17424'
down_revision: Union[str, None] = ('bc842fe4de85', 'a75721b32c6e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
