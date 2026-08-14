"""
« Ma soirée » — les chiffres du serveur, sur son écran (Phase 17.3).

Premier risque de résiliation identifié par l'audit du 2026-08-14 : l'équipe
contourne l'outil, et le patron résilie sans jamais dire pourquoi. Le serveur
utilise son téléphone, sa batterie, son forfait, et un rapport nominatif mesure
son temps de prise en charge — s'il n'y trouve rien pour lui, il a raison de le
contourner.

Cet écran lui rend ses propres chiffres. La règle qui le rend acceptable est
aussi importante que la fonctionnalité : **il ne voit que les siens.** Le
classement d'équipe reste un document de direction (14.2). Le jour où un serveur
se découvre comparé publiquement à ses collègues, l'équipe est perdue.
"""
from datetime import datetime, timedelta, timezone

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


def _taken_order(db_session, restaurant, table, item, staff, amount, claim_seconds=60, status=OrderStatus.SERVED):
    created = datetime.now(timezone.utc) - timedelta(minutes=30)
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=status,
        created_at=created,
        taken_by_staff_id=staff.id,
        taken_at=created + timedelta(seconds=claim_seconds),
    )
    order.items.append(
        OrderItem(menu_item_id=item.id, menu_item_name="Couscous", unit_price=amount, quantity=1)
    )
    db_session.add(order)
    db_session.commit()
    return order


def _ma_soiree(client, staff) -> dict:
    response = client.get("/api/v1/stats/ma-soiree", headers=auth_headers(staff))
    assert response.status_code == 200, response.text
    return response.json()


def test_a_waiter_sees_his_own_evening(client, db_session, resto):
    restaurant, table, item = resto
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    _taken_order(db_session, restaurant, table, item, sami, 20.0, claim_seconds=40)
    _taken_order(db_session, restaurant, table, item, sami, 30.0, claim_seconds=80)

    body = _ma_soiree(client, sami)

    assert body["orders_taken"] == 2
    assert body["total_amount_handled"] == pytest.approx(50.0)
    assert body["avg_seconds_to_claim"] == pytest.approx(60.0)


def test_he_never_sees_the_orders_of_a_colleague(client, db_session, resto):
    """La règle qui rend l'écran acceptable par l'équipe."""
    restaurant, table, item = resto
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    nadia = create_staff(restaurant.id, StaffRole.WAITER)
    _taken_order(db_session, restaurant, table, item, sami, 20.0)
    _taken_order(db_session, restaurant, table, item, nadia, 500.0)

    body = _ma_soiree(client, sami)

    assert body["orders_taken"] == 1
    assert body["total_amount_handled"] == pytest.approx(20.0)


def test_the_answer_carries_no_colleague_name_or_ranking(client, db_session, resto):
    """Aucun classement, aucun nom d'autrui : ni dans l'écran, ni dans la
    réponse — ce qui n'est pas envoyé ne peut pas fuiter dans une future UI."""
    restaurant, table, item = resto
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    nadia = create_staff(restaurant.id, StaffRole.WAITER)
    _taken_order(db_session, restaurant, table, item, nadia, 500.0)
    _taken_order(db_session, restaurant, table, item, sami, 20.0)

    raw = client.get("/api/v1/stats/ma-soiree", headers=auth_headers(sami)).text

    assert nadia.name not in raw
    assert "rank" not in raw and "classement" not in raw


def test_a_cancelled_order_does_not_count(client, db_session, resto):
    restaurant, table, item = resto
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    _taken_order(db_session, restaurant, table, item, sami, 20.0)
    _taken_order(db_session, restaurant, table, item, sami, 99.0, status=OrderStatus.CANCELLED)

    assert _ma_soiree(client, sami)["orders_taken"] == 1


def test_a_quiet_start_of_shift_shows_zero(client, db_session, resto):
    """Zéro et « aucune donnée » ne sont pas la même chose : le délai moyen est
    nul tant qu'aucune commande n'a été prise, le compteur vaut zéro."""
    restaurant, _table, _item = resto
    sami = create_staff(restaurant.id, StaffRole.WAITER)

    body = _ma_soiree(client, sami)

    assert body["orders_taken"] == 0
    assert body["total_amount_handled"] == 0
    assert body["avg_seconds_to_claim"] is None


def test_yesterdays_orders_are_not_counted_tonight(client, db_session, resto):
    restaurant, table, item = resto
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    order = _taken_order(db_session, restaurant, table, item, sami, 20.0)
    order.created_at = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()

    assert _ma_soiree(client, sami)["orders_taken"] == 0


def test_the_kitchen_also_gets_its_own_screen(client, db_session, resto):
    """Le poste chaud prend rarement des commandes : l'écran doit répondre zéro
    proprement plutôt que refuser l'accès."""
    restaurant, _table, _item = resto
    cuisine = create_staff(restaurant.id, StaffRole.KITCHEN)

    assert _ma_soiree(client, cuisine)["orders_taken"] == 0


def test_the_route_requires_authentication(client):
    """Aucun `restaurant_id` dans l'URL : le serveur est identifié par son seul
    JWT, donc rien à deviner et rien à énumérer."""
    assert client.get("/api/v1/stats/ma-soiree").status_code == 401
