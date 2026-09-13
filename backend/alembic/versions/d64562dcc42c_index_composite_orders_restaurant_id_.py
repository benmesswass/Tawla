"""index composite orders (restaurant_id, created_at)

Revision ID: d64562dcc42c
Revises: f97408ed1c1a
Create Date: 2026-09-11 08:01:16.647267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd64562dcc42c'
down_revision: Union[str, None] = 'f97408ed1c1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `CREATE INDEX` simple, PAS `CONCURRENTLY`, et c'est délibéré
    # (ROADMAP_PRODUCTION.md §P2.3).
    #
    # `CONCURRENTLY` évite le verrou d'écriture pendant la construction, ce qui
    # compte sur une table déjà grosse — mais une migration ne s'applique
    # qu'UNE fois par base, maintenant, sur une table qui compte quelques
    # milliers de lignes. Les 73 000 commandes/an/restaurant qui justifient cet
    # index sont l'état FUTUR, celui où il existera déjà. Le verrou se mesure
    # donc en millisecondes, et `CONCURRENTLY` protégerait d'un scénario qui ne
    # peut pas se produire pour cette migration-ci, au prix d'un
    # `autocommit_block()`, d'une branche par dialecte (la suite rejoue les
    # migrations sur SQLite) et du risque d'index INVALID à nettoyer à la main
    # en cas d'échec.
    #
    # La règle pour la prochaine fois : indexer une table DÉJÀ volumineuse en
    # production demande `CONCURRENTLY`, celle-ci non.
    op.create_index('ix_orders_restaurant_created', 'orders', ['restaurant_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_orders_restaurant_created', table_name='orders')
