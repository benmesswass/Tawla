"""merge roster/paiements avec occupation de table

Revision ID: f97408ed1c1a
Revises: 160fb87d49f5, f4b8d2a916c3
Create Date: 2026-09-10 00:34:02.723598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f97408ed1c1a'
down_revision: Union[str, None] = ('160fb87d49f5', 'f4b8d2a916c3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
