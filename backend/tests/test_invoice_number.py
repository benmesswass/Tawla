"""
Numérotation continue des factures — France, MARCHE_FRANCE.md Phase F5 (S2),
exigence du CGI art. 289 / arrêté du 3 octobre 1983.

Deux propriétés à ne jamais casser, et qui motivent chaque test ici :
- **continuité par restaurant** — la séquence est propre à l'émetteur, jamais
  dérivée d'`Order.id` (troué par les commandes annulées, et partagé entre
  tous les restaurants) ;
- **immuabilité** — une facture émise garde son numéro, un règlement rejoué
  n'en consomme jamais un second.

`current_market` est basculé sur FRANCE là où c'est nécessaire : sur le
marché tunisien (défaut des tests), aucun numéro n'est attribué du tout —
c'est le critère de sortie de la Phase F3, vérifié explicitement plus bas.
"""
from datetime import datetime, timezone

import pytest

from app.core import invoice_number as invoice_number_module
from app.core.invoice_number import ensure_invoice_number, format_invoice_number
from app.core.markets import FRANCE, TUNISIA
from app.modules.orders.models import InvoiceCounter, Order, PaymentStatus
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant
from tests.conftest import auth_headers, create_restaurant, create_staff


def _paid_order(db_session, restaurant: Restaurant, *, paid_at: datetime | None = None) -> Order:
    """Commande payée minimale, créée directement en base : cette suite teste
    l'attribution du numéro, pas le parcours de paiement (couvert ailleurs)."""
    from app.modules.tables.models import Table

    table = Table(restaurant_id=restaurant.id, label="Table 1")
    db_session.add(table)
    db_session.flush()
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        payment_status=PaymentStatus.PAID,
        paid_at=paid_at or datetime(2026, 6, 15, 20, 0, tzinfo=timezone.utc),
    )
    db_session.add(order)
    db_session.flush()
    return order


def test_format_is_year_prefixed_and_zero_padded():
    assert format_invoice_number(2026, 1) == "F2026-00001"
    assert format_invoice_number(2026, 42) == "F2026-00042"
    assert format_invoice_number(2027, 99999) == "F2027-99999"


def test_no_number_is_assigned_on_a_market_without_an_invoice_obligation(db_session):
    """Critère de sortie de la Phase F3 : `MARKET=tn` ne change pas de
    comportement. Aucun numéro, et aucune ligne de compteur créée."""
    restaurant = create_restaurant(slug="invoice-number-tn")
    order = _paid_order(db_session, restaurant)

    assert ensure_invoice_number(db_session, order, market=TUNISIA) is None
    assert order.invoice_number is None
    assert db_session.query(InvoiceCounter).count() == 0


def test_first_invoice_of_the_year_starts_at_one(db_session):
    restaurant = create_restaurant(slug="invoice-number-first")
    order = _paid_order(db_session, restaurant)

    assert ensure_invoice_number(db_session, order, market=FRANCE) == "F2026-00001"
    assert order.invoice_number == "F2026-00001"


def test_numbers_are_continuous_within_a_restaurant(db_session):
    restaurant = create_restaurant(slug="invoice-number-continuous")
    numbers = [
        ensure_invoice_number(db_session, _paid_order(db_session, restaurant), market=FRANCE) for _ in range(3)
    ]

    assert numbers == ["F2026-00001", "F2026-00002", "F2026-00003"]


def test_each_restaurant_has_its_own_sequence(db_session):
    """L'émetteur légal est le restaurant, jamais Tawla : deux restaurants
    émettent chacun leur `F2026-00001`, une séquence globale ferait au
    contraire un trou dans celle de chacun."""
    first = create_restaurant(slug="invoice-number-resto-a")
    second = create_restaurant(slug="invoice-number-resto-b")

    assert ensure_invoice_number(db_session, _paid_order(db_session, first), market=FRANCE) == "F2026-00001"
    assert ensure_invoice_number(db_session, _paid_order(db_session, second), market=FRANCE) == "F2026-00001"
    assert ensure_invoice_number(db_session, _paid_order(db_session, first), market=FRANCE) == "F2026-00002"


def test_the_sequence_restarts_at_one_each_year(db_session):
    restaurant = create_restaurant(slug="invoice-number-new-year")
    in_2026 = _paid_order(db_session, restaurant, paid_at=datetime(2026, 12, 20, 20, 0, tzinfo=timezone.utc))
    in_2027 = _paid_order(db_session, restaurant, paid_at=datetime(2027, 3, 4, 20, 0, tzinfo=timezone.utc))

    assert ensure_invoice_number(db_session, in_2026, market=FRANCE) == "F2026-00001"
    assert ensure_invoice_number(db_session, in_2027, market=FRANCE) == "F2027-00001"


def test_a_payment_just_after_midnight_belongs_to_the_previous_service_day_year(db_session):
    """Le millésime suit la journée de SERVICE (fin à 5h, core/dates.py), pas
    l'horloge : une commande payée le 1er janvier à 00h30 appartient au
    service du 31 décembre, donc à l'année précédente. Sans ça, le réveillon
    ouvrirait la séquence de l'année suivante en plein service."""
    restaurant = create_restaurant(slug="invoice-number-new-year-eve")
    # 2027-01-01 00h30 à Paris = 2026-12-31 23h30 UTC.
    order = _paid_order(db_session, restaurant, paid_at=datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc))

    assert ensure_invoice_number(db_session, order, market=FRANCE) == "F2026-00001"


def test_an_already_numbered_order_keeps_its_number(db_session):
    """Immuabilité : un règlement rejoué (webhook + page de retour
    concurrents, voir orders/service.py::settle_card_payment) ne doit jamais
    consommer un second numéro pour la même facture."""
    restaurant = create_restaurant(slug="invoice-number-idempotent")
    order = _paid_order(db_session, restaurant)

    first = ensure_invoice_number(db_session, order, market=FRANCE)
    second = ensure_invoice_number(db_session, order, market=FRANCE)

    assert first == second == "F2026-00001"
    counter = db_session.query(InvoiceCounter).filter_by(restaurant_id=restaurant.id).one()
    assert counter.last_number == 1


def test_a_cancelled_order_never_consumes_a_number(db_session):
    """La continuité est ce qui rend la séquence vérifiable : seule une
    commande PAYÉE reçoit un numéro, donc aucune annulation ne peut créer un
    trou (`ensure_invoice_number` n'est appelée que depuis les chemins de
    paiement confirmé — voir orders/service.py)."""
    restaurant = create_restaurant(slug="invoice-number-cancelled")
    first = _paid_order(db_session, restaurant)
    ensure_invoice_number(db_session, first, market=FRANCE)

    cancelled = _paid_order(db_session, restaurant)
    cancelled.payment_status = PaymentStatus.UNPAID
    db_session.flush()

    third = _paid_order(db_session, restaurant)

    assert ensure_invoice_number(db_session, third, market=FRANCE) == "F2026-00002"
    assert cancelled.invoice_number is None


# --- Bout en bout : le numéro est posé par le parcours de paiement réel -----


@pytest.fixture
def _france_invoicing(monkeypatch):
    monkeypatch.setattr(invoice_number_module, "current_market", FRANCE)


def _manager_headers(restaurant_id: int) -> dict[str, str]:
    return auth_headers(create_staff(restaurant_id, StaffRole.MANAGER))


def _order_ready_to_pay(client, restaurant: Restaurant, *, price: float = 30) -> dict:
    manager_headers = _manager_headers(restaurant.id)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": price},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)
    return order


def test_confirming_a_cash_payment_assigns_the_invoice_number(client, db_session, _france_invoicing):
    restaurant = create_restaurant(slug="invoice-number-cash-e2e")
    order = _order_ready_to_pay(client, restaurant)
    from tests.conftest import order_headers

    client.post(f"/api/v1/orders/{order['id']}/pay/cash", json={"tip_amount": 0}, headers=order_headers(order))
    res = client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=_manager_headers(restaurant.id))

    assert res.status_code == 200
    db_order = db_session.get(Order, order["id"])
    db_session.refresh(db_order)
    assert db_order.invoice_number is not None
    assert db_order.invoice_number.startswith("F")


def test_the_tunisian_payment_path_still_assigns_no_number(client, db_session):
    """Même parcours, marché par défaut (Tunisie) : rien ne change."""
    restaurant = create_restaurant(slug="invoice-number-cash-tn-e2e")
    order = _order_ready_to_pay(client, restaurant)
    from tests.conftest import order_headers

    client.post(f"/api/v1/orders/{order['id']}/pay/cash", json={"tip_amount": 0}, headers=order_headers(order))
    res = client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=_manager_headers(restaurant.id))

    assert res.status_code == 200
    db_order = db_session.get(Order, order["id"])
    db_session.refresh(db_order)
    assert db_order.invoice_number is None
