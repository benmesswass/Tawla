"""add card_terminal payment method and customer_email to orders

Revision ID: c3f81a9e2b56
Revises: b7e2a5c9d104
Create Date: 2026-08-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f81a9e2b56'
down_revision: Union[str, None] = 'b7e2a5c9d104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_ENUM = ("CARD", "CASH")
_NEW_ENUM = ("CARD", "CARD_TERMINAL", "CASH")


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # Type enum nommé, réel côté Postgres — ADD VALUE ne peut pas être
        # annulé (pas de downgrade possible, voir plus bas).
        op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'CARD_TERMINAL'")
    else:
        # SQLite (tests, dev local) : l'enum est une simple colonne texte de
        # longueur fixe (max des valeurs) — sans ce redimensionnement, la
        # comparaison schéma migré / modèles (test_migrations.py) diverge dès
        # qu'une valeur plus longue que 'CARD'/'CASH' est ajoutée au modèle.
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "payment_method",
                existing_type=sa.Enum(*_OLD_ENUM, name="paymentmethod"),
                type_=sa.Enum(*_NEW_ENUM, name="paymentmethod"),
            )

    op.add_column(
        'orders',
        sa.Column('customer_email', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('orders', 'customer_email')

    if op.get_bind().dialect.name != "postgresql":
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "payment_method",
                existing_type=sa.Enum(*_NEW_ENUM, name="paymentmethod"),
                type_=sa.Enum(*_OLD_ENUM, name="paymentmethod"),
            )
    # Côté Postgres, la valeur d'enum ajoutée n'est pas retirée : Postgres ne
    # permet pas de supprimer une valeur d'un type enum existant.
