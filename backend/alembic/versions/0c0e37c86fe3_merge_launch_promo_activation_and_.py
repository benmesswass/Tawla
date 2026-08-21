"""merge launch promo activation and platform admin branches

Revision ID: 0c0e37c86fe3
Revises: cb1a4204472f, e0a7b7b1aad3
Create Date: 2026-08-21 08:35:31.780648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c0e37c86fe3'
down_revision: Union[str, None] = ('cb1a4204472f', 'e0a7b7b1aad3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
