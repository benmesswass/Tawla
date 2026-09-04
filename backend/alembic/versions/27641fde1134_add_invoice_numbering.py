"""add invoice numbering

Revision ID: 27641fde1134
Revises: b7d3f19a6c42
Create Date: 2026-09-03 18:06:02.704612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27641fde1134'
down_revision: Union[str, None] = 'b7d3f19a6c42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Séquence de numérotation par (restaurant, année) — l'émetteur légal de
    # la note est le restaurant, jamais Tawla (voir core/invoice_number.py).
    op.create_table(
        'invoice_counters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        # Dernier numéro ATTRIBUÉ, pas le prochain : une ligne fraîche vaut 0.
        sa.Column('last_number', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('restaurant_id', 'year', name='uq_invoice_counter_restaurant_year'),
    )
    op.create_index(op.f('ix_invoice_counters_restaurant_id'), 'invoice_counters', ['restaurant_id'])

    # Nullable : null tant que la commande n'est pas payée, et sur tout
    # marché sans obligation de note (Tunisie). Unicité PAR RESTAURANT, pas
    # globale : la séquence appartient à l'émetteur, donc deux restaurants
    # portent chacun leur `F2026-00001` — une contrainte globale les ferait
    # entrer en collision. Garde-fou de dernier recours si le verrou du
    # compteur venait à sauter (deux règlements concurrents).
    # batch_alter_table : SQLite ne sait pas ajouter une contrainte à une
    # table existante (copie-et-remplace ici, ALTER TABLE natif sur Postgres,
    # la cible réelle) — même motif que cc0f0456fb36.
    op.add_column('orders', sa.Column('invoice_number', sa.String(length=30), nullable=True))
    with op.batch_alter_table('orders') as batch:
        batch.create_unique_constraint('uq_orders_restaurant_invoice_number', ['restaurant_id', 'invoice_number'])


def downgrade() -> None:
    with op.batch_alter_table('orders') as batch:
        batch.drop_constraint('uq_orders_restaurant_invoice_number', type_='unique')
    op.drop_column('orders', 'invoice_number')
    op.drop_index(op.f('ix_invoice_counters_restaurant_id'), table_name='invoice_counters')
    op.drop_table('invoice_counters')
