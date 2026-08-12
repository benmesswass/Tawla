"""add subscription_tier to restaurants

Revision ID: 5b27b85b11ec
Revises: 81067c492c21
Create Date: 2026-08-12 10:54:43.305013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5b27b85b11ec'
down_revision: Union[str, None] = '81067c492c21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_NAME = "subscriptiontier"
_ENUM_VALUES = ("ESSENTIEL", "PRO", "BUSINESS")


def upgrade() -> None:
    # ALTER TABLE ADD COLUMN avec un type Enum Postgres n'émet pas le
    # CREATE TYPE automatiquement (contrairement à CREATE TABLE) — il faut
    # le créer explicitement avant, avec create_type=False sur la colonne
    # pour éviter une double création.
    subscription_tier_enum = postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME)
    subscription_tier_enum.create(op.get_bind(), checkfirst=True)

    # server_default nécessaire : la colonne est NOT NULL et la table a déjà
    # des lignes (restaurants existants) — sans lui, l'ALTER TABLE échoue.
    # Les paliers n'ont aucune fonctionnalité bloquée pour l'instant (cf.
    # SubscriptionTier), donc "essentiel" par défaut pour tout le monde
    # n'a aucun effet visible tant que le gating n'est pas activé.
    op.add_column(
        'restaurants',
        sa.Column(
            'subscription_tier',
            postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=False,
            server_default='ESSENTIEL',
        ),
    )


def downgrade() -> None:
    op.drop_column('restaurants', 'subscription_tier')
    postgresql.ENUM(name=_ENUM_NAME).drop(op.get_bind(), checkfirst=True)
