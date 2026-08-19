"""add konnect credentials to restaurants

Revision ID: b7e2a5c9d104
Revises: a4d92e6c1f08
Create Date: 2026-08-19 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2a5c9d104'
down_revision: Union[str, None] = 'a4d92e6c1f08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Modèle direct (2026-08-19) : le client règle le compte du RESTAURANT,
    # jamais celui de Tawla — chaque établissement connecte donc son propre
    # wallet Konnect. Nullable sans défaut : tant qu'un restaurant n'a rien
    # connecté, le paiement carte reste en mode démo (dégradation gracieuse,
    # voir app/core/konnect.py).
    op.add_column(
        'restaurants',
        sa.Column('konnect_api_key_encrypted', sa.String(500), nullable=True),
    )
    op.add_column(
        'restaurants',
        sa.Column('konnect_wallet_id', sa.String(120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('restaurants', 'konnect_wallet_id')
    op.drop_column('restaurants', 'konnect_api_key_encrypted')
