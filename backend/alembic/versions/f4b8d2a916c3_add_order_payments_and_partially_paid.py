"""add order_payments table and partially_paid status

Revision ID: f4b8d2a916c3
Revises: a7e2f9c14b6d
Create Date: 2026-09-09 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f4b8d2a916c3'
down_revision: Union[str, None] = 'a7e2f9c14b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_STATUS_ENUM = ("UNPAID", "PENDING", "PAID")
_NEW_STATUS_ENUM = ("UNPAID", "PENDING", "PARTIALLY_PAID", "PAID")


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # Type enum nommé, réel côté Postgres — ADD VALUE ne peut pas être
        # annulé (pas de downgrade possible, voir plus bas), même principe
        # que c3f81a9e2b56 pour CARD_TERMINAL.
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'PARTIALLY_PAID'")
    else:
        # SQLite (tests, dev local) : l'enum est une simple colonne texte —
        # redimensionnée pour la comparaison schéma migré / modèles
        # (test_migrations.py) reste correcte avec la valeur la plus longue.
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "payment_status",
                existing_type=sa.Enum(*_OLD_STATUS_ENUM, name="paymentstatus"),
                type_=sa.Enum(*_NEW_STATUS_ENUM, name="paymentstatus"),
            )

    op.create_table(
        'order_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('payer_key', sa.String(length=80), nullable=False),
        sa.Column('payer_name', sa.String(length=40), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tip_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            'method',
            postgresql.ENUM('CARD', 'CARD_TERMINAL', 'CASH', name='paymentmethod', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'PAID', name='orderpaymentstatus'),
            nullable=False,
        ),
        sa.Column('payment_ref', sa.String(length=120), nullable=True),
        sa.Column('customer_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_order_payments_order_id'), 'order_payments', ['order_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_order_payments_order_id'), table_name='order_payments')
    op.drop_table('order_payments')
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS orderpaymentstatus")
        # Côté Postgres, la valeur PARTIALLY_PAID ajoutée à `paymentstatus`
        # n'est pas retirée : Postgres ne permet pas de supprimer une valeur
        # d'un type enum existant (même limite que c3f81a9e2b56).
    else:
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "payment_status",
                existing_type=sa.Enum(*_NEW_STATUS_ENUM, name="paymentstatus"),
                type_=sa.Enum(*_OLD_STATUS_ENUM, name="paymentstatus"),
            )
