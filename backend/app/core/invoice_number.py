"""
Attribution du numéro de facture — France, MARCHE_FRANCE.md Phase F5 (S2).

Le CGI (art. 289) et l'arrêté du 3 octobre 1983 exigent une numérotation
**continue, chronologique et sans rupture** par émetteur. Trois conséquences
qui expliquent la forme de ce module :

- **Une séquence par restaurant**, jamais globale : l'émetteur de la note,
  c'est le restaurant, pas Tawla (même raisonnement que les Direct Charges
  côté paiement — voir core/stripe_gateway.py).
- **Jamais dérivé d'`Order.id`** : cet id est une séquence unique pour toute
  la base (multi-tenant, ADR-0002), donc troué pour un restaurant donné, et
  troué tout court dès qu'une commande est annulée ou jamais payée.
- **Attribué au paiement confirmé, une seule fois** : une commande non payée
  n'est pas une facture, et une facture émise ne change jamais de numéro.

Marché sans obligation de note (`Market.invoice_threshold is None`, la
Tunisie aujourd'hui) : aucun numéro attribué, aucune ligne de compteur
créée, le comportement tunisien reste inchangé au bit près — c'est le
critère de sortie de la Phase F3.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dates import service_day_start
from app.core.logging import get_logger, log_event
from app.core.markets import Market, current_market
from app.modules.orders.models import InvoiceCounter, Order, PaymentStatus

logger = get_logger("invoice_number")


def format_invoice_number(year: int, sequence: int) -> str:
    """`F2026-00001` — millésime explicite (la séquence repart à 1 chaque
    année civile) puis 5 chiffres, ce qui couvre 99 999 factures par an et
    par restaurant sans changer de format. Le préfixe `F` distingue une
    facture d'un numéro de commande à l'œil nu, sur un document où les deux
    apparaissent côte à côte."""
    return f"F{year}-{sequence:05d}"


def ensure_invoice_number(db: Session, order: Order, market: Market | None = None) -> str | None:
    """
    Attribue son numéro de facture définitif à une commande qui vient d'être
    payée, et le renvoie. Idempotent : une commande qui en a déjà un le
    conserve tel quel (un règlement rejoué — webhook + page de retour
    concurrents, voir orders/service.py::settle_card_payment — ne doit jamais
    consommer un second numéro).

    Renvoie `None` sans rien écrire sur un marché sans obligation de note.

    L'appelant commite : cette fonction `flush()` seulement, pour rester
    dans la transaction du paiement qui l'appelle — un numéro attribué à une
    commande dont le paiement échouerait ensuite serait un trou dans la
    séquence, exactement ce que la continuité interdit.

    `market=None` lit `current_market` À L'APPEL, jamais en argument par
    défaut : une valeur par défaut serait figée à l'import du module, donc
    insensible au marché réellement servi (et intestable) — même motif que
    `core/dates.py::_resolve_market`.
    """
    market = market or current_market
    if market.invoice_threshold is None:
        return None
    if order.invoice_number:
        return order.invoice_number

    # Un numéro de facture définitif ne doit jamais être brûlé sur une
    # commande dont le paiement n'est pas confirmé — cet invariant n'était
    # jusqu'ici garanti que par la discipline des appelants (revue de code).
    assert order.payment_status == PaymentStatus.PAID, (
        f"ensure_invoice_number appelé sur la commande {order.id} avec "
        f"payment_status={order.payment_status!r} au lieu de PAID"
    )

    # Millésime pris sur la journée de SERVICE (fuseau du marché), jamais sur
    # l'UTC brut : une commande payée à 00h30 appartient au service de la
    # veille (core/dates.py), et donc à l'année de la veille au réveillon.
    year = service_day_start(order.paid_at, market).year

    # `with_for_update()` : deux tables qui paient dans la même seconde
    # doivent recevoir deux numéros distincts. Sans le verrou, les deux
    # lisent le même `last_number` et repartent avec le même numéro — la
    # contrainte d'unicité sur `Order.invoice_number` ferait alors échouer un
    # paiement déjà encaissé. Sans effet sur SQLite (tests), qui sérialise
    # déjà les écritures.
    counter = db.execute(
        select(InvoiceCounter)
        .where(InvoiceCounter.restaurant_id == order.restaurant_id, InvoiceCounter.year == year)
        .with_for_update()
    ).scalar_one_or_none()

    if counter is None:
        # Deux premiers paiements de l'année pour ce restaurant, dans la même
        # seconde : les deux SELECT ci-dessus renvoient `None` (la ligne
        # n'existe pas encore, `with_for_update()` ne verrouille rien), donc
        # les deux tentent l'INSERT. Le perdant lève IntegrityError sur la
        # contrainte d'unicité (restaurant_id, year) ; on rejoue alors le
        # SELECT verrouillé pour récupérer la ligne que le gagnant vient de
        # committer, au lieu de laisser planter un paiement pourtant encaissé.
        try:
            with db.begin_nested():
                counter = InvoiceCounter(restaurant_id=order.restaurant_id, year=year, last_number=0)
                db.add(counter)
                db.flush()
        except IntegrityError:
            counter = db.execute(
                select(InvoiceCounter)
                .where(InvoiceCounter.restaurant_id == order.restaurant_id, InvoiceCounter.year == year)
                .with_for_update()
            ).scalar_one()

    counter.last_number += 1
    order.invoice_number = format_invoice_number(year, counter.last_number)
    db.flush()

    log_event(
        logger, "invoice.number_assigned",
        restaurant_id=order.restaurant_id, order_id=order.id, invoice_number=order.invoice_number,
    )
    return order.invoice_number
