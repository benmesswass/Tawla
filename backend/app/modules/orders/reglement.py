"""
Le règlement d'une TABLE — la seule réponse à « est-ce que cette table a payé ».

`payment_status` vit sur la commande, et une table qui commande en deux temps
en porte plusieurs (commandes ouvertes multiples, PR #52). Le serveur, lui, ne
raisonne jamais en commandes : il regarde une table et veut savoir s'il reste
quelque chose à encaisser avant de la libérer. Ce module agrège les commandes
en un état par table, **en lecture seule** — il ne construit aucune addition de
table (ce chantier-là reste sous condition, ROADMAP.md), il ne fait que
totaliser ce qui existe déjà.

Fenêtre : les commandes de l'occupation en cours (`Table.occupied_at`), avec la
journée de service comme plancher. Une table libérée puis réoccupée repart donc
à zéro — sinon le couple qui s'installe hériterait du règlement de la tablée
précédente.

`montant_encaisse` / `reste_a_encaisser` sont ici et pas dans les statistiques :
« ce qui est réellement rentré » est une question de paiement, et le dashboard
du patron comme l'écran du serveur doivent y répondre par le même calcul.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.dates import service_day_start
from app.modules.orders.models import (
    Order,
    OrderPayment,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.tables.models import Table

# Un dinar tunisien se divise en 1000 millimes : la tolérance de comparaison
# doit rester en dessous du millime, sinon « il reste 1 millime » deviendrait
# « entièrement réglée ». Même seuil que `_after_share_paid`.
TOLERANCE = 0.005

_JAMAIS = datetime.min.replace(tzinfo=timezone.utc)


def _en_utc(moment: datetime | None) -> datetime | None:
    """
    SQLite (tests, dev local) rend des datetimes naïfs là où Postgres rend des
    datetimes aware, et comparer les deux lève un `TypeError`. Tout ce qui sort
    de la base est de l'UTC — c'est ce que garantit l'écriture
    (`datetime.now(timezone.utc)` partout).
    """
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=timezone.utc)


def montant_encaisse(order: Order) -> float:
    """
    Ce qui est réellement rentré pour cette commande, pourboire exclu (comme
    `Order.amount_paid`, et comme la recette d'avant ce chantier).

    Le repli sur `total_amount` n'est pas une précaution de style : des
    commandes portent `payment_status = PAID` sans **aucune** ligne
    `OrderPayment`. La migration qui a introduit le paiement par personne
    (`f4b8d2a916c3`) n'a rien rétro-rempli, et le jeu de démonstration montré
    aux restaurateurs écrit le statut en direct (`modules/demo/historique.py`).
    Sans ce repli, leur recette tomberait à zéro du jour au lendemain.
    """
    if order.amount_paid > 0:
        return order.amount_paid
    if order.payment_status == PaymentStatus.PAID:
        return order.total_amount
    return 0.0


def reste_a_encaisser(order: Order) -> float:
    """Le pendant de `montant_encaisse` — jamais `amount_remaining` seul, qui
    compterait une commande payée sans ligne de paiement comme entièrement
    due."""
    return max(0.0, order.total_amount - montant_encaisse(order))


@dataclass(frozen=True)
class PartReglee:
    """Une part effectivement encaissée, telle que le serveur la relit."""

    payment_id: int
    order_id: int
    method: PaymentMethod
    payer_name: str
    amount: float
    tip_amount: float
    paid_at: datetime | None
    collected_by_name: str | None


@dataclass(frozen=True)
class CommandeDue:
    """
    Une commande de la table sur laquelle il reste quelque chose à encaisser.

    Nécessaire parce qu'un encaissement s'applique à UNE commande (c'est là que
    vivent `payment_status` et la facture) alors que le serveur, lui, encaisse
    une table. Une table qui a commandé en deux temps a deux additions : sans
    cette liste, l'écran ne saurait pas laquelle régler.
    """

    order_id: int
    amount_remaining: float


@dataclass(frozen=True)
class ReglementDeTable:
    table_id: int
    table_label: str
    total_amount: float
    amount_paid: float
    amount_remaining: float
    fully_paid: bool
    orders_count: int
    last_paid_at: datetime | None
    parts: list[PartReglee] = field(default_factory=list)
    dues: list[CommandeDue] = field(default_factory=list)


def _parts_reglees(orders: list[Order]) -> list[PartReglee]:
    parts = [
        PartReglee(
            payment_id=payment.id,
            order_id=order.id,
            method=payment.method,
            payer_name=payment.payer_name,
            amount=float(payment.amount),
            tip_amount=float(payment.tip_amount),
            paid_at=_en_utc(payment.paid_at),
            collected_by_name=payment.collected_by_name,
        )
        for order in orders
        for payment in order.payments
        if payment.status == OrderPaymentStatus.PAID
    ]
    # Le dernier encaissement en premier : c'est celui dont le serveur veut la
    # confirmation quand il vient de l'encaisser. Sentinelle plutôt qu'un tri
    # sur `None`, qui lèverait un TypeError sur deux parts sans horodatage —
    # même repli que `_after_share_paid`.
    return sorted(parts, key=lambda p: p.paid_at or _JAMAIS, reverse=True)


def _agreger(table: Table, orders: list[Order]) -> ReglementDeTable:
    total = sum(order.total_amount for order in orders)
    encaisse = sum(montant_encaisse(order) for order in orders)
    restant = sum(reste_a_encaisser(order) for order in orders)
    parts = _parts_reglees(orders)
    return ReglementDeTable(
        table_id=table.id,
        table_label=table.label,
        total_amount=total,
        amount_paid=encaisse,
        amount_remaining=restant,
        # Une table sans commande n'est pas « réglée » : il n'y a rien à
        # régler, et une pastille verte sur une table vide ne veut rien dire.
        fully_paid=bool(orders) and restant <= TOLERANCE,
        orders_count=len(orders),
        last_paid_at=parts[0].paid_at if parts else None,
        parts=parts,
        # Dans l'ordre d'arrivée (celui de la requête) : la plus ancienne
        # addition se règle d'abord, comme en salle.
        dues=[
            CommandeDue(order_id=order.id, amount_remaining=reste_a_encaisser(order))
            for order in orders
            if reste_a_encaisser(order) > TOLERANCE
        ],
    )


def _dans_la_fenetre(order: Order, table: Table) -> bool:
    """Une table libérée puis réoccupée repart à zéro : tout ce qui précède
    l'occupation en cours appartient à la tablée précédente."""
    debut = _en_utc(table.occupied_at)
    if debut is None:
        return True
    cree = _en_utc(order.created_at)
    return cree is not None and cree >= debut


def _charger_commandes(db: Session, restaurant_id: int | None = None, table_id: int | None = None) -> list[Order]:
    query = (
        db.query(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments).selectinload(OrderPayment.collected_by),
            selectinload(Order.table),
        )
        .filter(
            Order.status != OrderStatus.CANCELLED,
            # Même borne de journée de service que `list_active_orders` : les
            # écrans de service doivent s'accorder sur ce qu'est « aujourd'hui ».
            Order.created_at >= service_day_start(),
        )
    )
    if restaurant_id is not None:
        query = query.filter(Order.restaurant_id == restaurant_id)
    if table_id is not None:
        query = query.filter(Order.table_id == table_id)
    return query.order_by(Order.created_at).all()


def reglement_de_table(db: Session, table: Table) -> ReglementDeTable:
    """L'état de règlement d'UNE table — ce que porte la diffusion WebSocket
    au moment où une part vient d'être encaissée."""
    orders = [order for order in _charger_commandes(db, table_id=table.id) if _dans_la_fenetre(order, table)]
    return _agreger(table, orders)


def reglements_du_restaurant(db: Session, restaurant_id: int) -> list[ReglementDeTable]:
    """
    Le rechargement de l'écran serveur : une ligne par table qui a quelque
    chose à dire aujourd'hui. Une seule requête pour toute la salle — cet
    écran se recharge en plein service, une requête par table n'y a pas sa
    place (même principe que `list_active_orders`).

    Les tables sans commande dans la fenêtre sont absentes de la réponse, pas
    présentes à zéro : l'écran n'a rien à en afficher.
    """
    par_table: dict[int, list[Order]] = {}
    tables: dict[int, Table] = {}
    for order in _charger_commandes(db, restaurant_id=restaurant_id):
        table = order.table
        if not _dans_la_fenetre(order, table):
            continue
        tables[table.id] = table
        par_table.setdefault(table.id, []).append(order)
    return [_agreger(tables[table_id], orders) for table_id, orders in par_table.items()]
