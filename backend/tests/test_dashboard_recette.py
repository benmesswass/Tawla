"""
Le premier écran du patron (Phase 17.1).

Le tableau de bord affichait les temps par étape, la performance par serveur,
les plats les plus vendus — jamais « voilà ce que tu as fait aujourd'hui ».
C'est pourtant le seul chiffre qu'un restaurateur cherche tous les soirs. Sans
lui le tableau de bord est une curiosité qu'on ouvre quand on y pense ; avec
lui c'est une habitude quotidienne, et c'est cette habitude qui empêche une
résiliation au troisième mois.

Les commandes perdues sont posées juste à côté : c'est ainsi que le patron
apprend le chiffre qui justifie l'abonnement — **en passant**, pendant qu'il
regarde sa recette.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


@pytest.fixture()
def resto(db_session):
    restaurant = create_restaurant(name="Chez Slah")
    table = Table(restaurant_id=restaurant.id, label="Terrasse 2")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


def _order(db_session, restaurant, table, item, amount: float, status: OrderStatus, minutes_ago: int = 1):
    """Commande posée directement en base : ces tests portent sur le calcul,
    pas sur le parcours (couvert ailleurs)."""
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=status,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    order.items.append(
        OrderItem(menu_item_id=item.id, menu_item_name="Couscous", unit_price=amount, quantity=1)
    )
    db_session.add(order)
    db_session.commit()
    return order


def _dashboard(client, restaurant, staff) -> dict:
    response = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(staff))
    assert response.status_code == 200, response.text
    return response.json()


def test_the_dashboard_shows_todays_takings(client, db_session, resto):
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 32.5, OrderStatus.READY)

    body = _dashboard(client, restaurant, manager)

    assert body["revenue_today"] == pytest.approx(52.5), (
        "le patron ne voit nulle part ce qu'il a fait aujourd'hui"
    )


def test_a_cancelled_order_is_not_counted_as_takings(client, db_session, resto):
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 99.0, OrderStatus.CANCELLED)

    assert _dashboard(client, restaurant, manager)["revenue_today"] == pytest.approx(20.0)


def test_the_dashboard_shows_todays_lost_orders(client, db_session, resto):
    """Annulée, plus jamais prise en charge au-delà du seuil d'abandon."""
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 30.0, OrderStatus.CANCELLED)
    _order(db_session, restaurant, table, item, 25.0, OrderStatus.PENDING_CONFIRMATION, minutes_ago=45)
    # Celle-ci vient d'arriver : elle n'est pas perdue, elle attend.
    _order(db_session, restaurant, table, item, 18.0, OrderStatus.PENDING_CONFIRMATION, minutes_ago=1)

    assert _dashboard(client, restaurant, manager)["lost_orders_today"] == 2


def test_takings_and_lost_orders_match_the_proof_page(client, db_session, resto):
    """
    Les deux écrans doivent dire la même chose du même jour. S'ils divergent,
    le patron ne croit plus ni l'un ni l'autre — et c'est sur ces chiffres que
    repose toute la vente.
    """
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 30.0, OrderStatus.READY)
    _order(db_session, restaurant, table, item, 40.0, OrderStatus.CANCELLED)
    _order(db_session, restaurant, table, item, 25.0, OrderStatus.PENDING_CONFIRMATION, minutes_ago=45)

    dashboard = _dashboard(client, restaurant, manager)
    today = date.today().isoformat()
    proof = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}?start={today}&end={today}",
        headers=auth_headers(manager),
    ).json()["current"]

    assert dashboard["lost_orders_today"] == proof["lost_orders_count"]
    # La recette est la somme des paniers non annulés, dont la page de preuve
    # tire sa moyenne : les deux écrans partagent la même définition.
    non_cancelled = proof["orders_count"] - proof["cancelled_count"]
    assert dashboard["revenue_today"] == pytest.approx(proof["avg_basket_amount"] * non_cancelled)


def test_a_quiet_day_shows_zero_and_not_an_empty_screen(client, db_session, resto):
    """Zéro est une information ; une case vide est un bug aux yeux du patron."""
    restaurant, _table, _item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    body = _dashboard(client, restaurant, manager)

    assert body["revenue_today"] == 0
    assert body["lost_orders_today"] == 0


def test_the_takings_of_another_restaurant_are_never_visible(client, db_session, resto):
    restaurant, table, item = resto
    autre = create_restaurant(name="Le Concurrent")
    manager_autre = create_staff(autre.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 500.0, OrderStatus.SERVED)

    response = client.get(
        f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(manager_autre)
    )

    assert response.status_code in (403, 404)


def test_a_waiter_cannot_read_the_takings(client, db_session, resto):
    """La recette est un chiffre de direction, pas un chiffre de salle."""
    restaurant, table, item = resto
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)

    response = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(waiter))

    assert response.status_code == 403
