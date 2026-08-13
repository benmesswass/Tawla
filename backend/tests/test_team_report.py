"""
Rapport d'équipe par période (Phase 14.2).

C'est la base d'une prime de rendement : les chiffres doivent être ceux qu'un
serveur peut reconnaître comme siens, et le document doit rester réservé au
manager — un classement affiché en salle transformerait l'outil en surveillance
et l'équipe le saboterait.
"""
from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _setup(db_session, slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=slug)
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


def _order(db_session, restaurant, table, item, *, staff=None, days_ago=1.0,
           claim_after_seconds=None, quantity=1, status=OrderStatus.SERVED):
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=status,
        created_at=created,
        taken_by_staff_id=staff.id if staff else None,
        taken_at=created + timedelta(seconds=claim_after_seconds) if claim_after_seconds else None,
    )
    order.items.append(
        OrderItem(
            menu_item_id=item.id, menu_item_name=item.name, unit_price=item.price, quantity=quantity
        )
    )
    db_session.add(order)
    db_session.commit()
    return order


def _report(client, restaurant, manager, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"/api/v1/stats/equipe/{restaurant.id}" + (f"?{query}" if query else "")
    response = client.get(url, headers=auth_headers(manager))
    assert response.status_code == 200, response.text
    return response.json()


def test_counts_orders_delay_and_amount_per_staff(client, db_session):
    restaurant, table, item = _setup(db_session, "equipe-base")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    nadia = create_staff(restaurant.id, StaffRole.WAITER)

    _order(db_session, restaurant, table, item, staff=sami, claim_after_seconds=60, quantity=1)
    _order(db_session, restaurant, table, item, staff=sami, claim_after_seconds=120, quantity=2)
    _order(db_session, restaurant, table, item, staff=nadia, claim_after_seconds=30, quantity=1)

    rows = {r["staff_id"]: r for r in _report(client, restaurant, manager)["staff"]}
    assert rows[sami.id]["orders_taken"] == 2
    assert rows[sami.id]["avg_seconds_to_claim"] == 90.0
    assert rows[sami.id]["total_amount_handled"] == 60.0
    assert rows[nadia.id]["orders_taken"] == 1
    assert rows[nadia.id]["total_amount_handled"] == 20.0


def test_rows_are_sorted_by_volume(client, db_session):
    restaurant, table, item = _setup(db_session, "equipe-tri")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    nadia = create_staff(restaurant.id, StaffRole.WAITER)

    _order(db_session, restaurant, table, item, staff=nadia, claim_after_seconds=10)
    for _ in range(3):
        _order(db_session, restaurant, table, item, staff=sami, claim_after_seconds=10)

    staff_rows = _report(client, restaurant, manager)["staff"]
    assert [r["staff_id"] for r in staff_rows] == [sami.id, nadia.id]


def test_cancelled_orders_do_not_count_towards_a_bonus(client, db_session):
    restaurant, table, item = _setup(db_session, "equipe-annulee")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    sami = create_staff(restaurant.id, StaffRole.WAITER)

    _order(db_session, restaurant, table, item, staff=sami, claim_after_seconds=60)
    _order(
        db_session, restaurant, table, item, staff=sami, claim_after_seconds=60,
        quantity=10, status=OrderStatus.CANCELLED,
    )

    row = _report(client, restaurant, manager)["staff"][0]
    assert row["orders_taken"] == 1
    assert row["total_amount_handled"] == 20.0


def test_orders_nobody_took_are_not_attributed(client, db_session):
    restaurant, table, item = _setup(db_session, "equipe-orpheline")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    _order(db_session, restaurant, table, item, staff=None)

    assert _report(client, restaurant, manager)["staff"] == []


def test_a_staff_member_who_left_still_appears(client, db_session):
    """Un serveur parti en milieu de mois a droit à sa prime : son compte est
    désactivé, pas son historique."""
    restaurant, table, item = _setup(db_session, "equipe-parti")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    sami = create_staff(restaurant.id, StaffRole.WAITER)
    _order(db_session, restaurant, table, item, staff=sami, claim_after_seconds=45)

    client.patch(
        f"/api/v1/staff/{sami.id}", json={"is_active": False}, headers=auth_headers(manager)
    )

    rows = _report(client, restaurant, manager)["staff"]
    assert [r["staff_id"] for r in rows] == [sami.id]


def test_period_bounds_are_respected(client, db_session):
    restaurant, table, item = _setup(db_session, "equipe-periode")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    sami = create_staff(restaurant.id, StaffRole.WAITER)

    _order(db_session, restaurant, table, item, staff=sami, days_ago=2, claim_after_seconds=10)
    _order(db_session, restaurant, table, item, staff=sami, days_ago=30, claim_after_seconds=10)

    # Par défaut, les 7 derniers jours.
    assert _report(client, restaurant, manager)["staff"][0]["orders_taken"] == 1


def test_report_is_isolated_and_manager_only(client, db_session):
    restaurant, table, item = _setup(db_session, "equipe-iso-a")
    other, other_table, other_item = _setup(db_session, "equipe-iso-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    other_waiter = create_staff(other.id, StaffRole.WAITER)

    _order(db_session, restaurant, table, item, staff=waiter, claim_after_seconds=10)
    _order(db_session, other, other_table, other_item, staff=other_waiter, claim_after_seconds=10)

    rows = _report(client, restaurant, manager)["staff"]
    assert [r["staff_id"] for r in rows] == [waiter.id]

    assert client.get(f"/api/v1/stats/equipe/{other.id}", headers=auth_headers(manager)).status_code == 403
    # Un serveur ne consulte pas le document qui sert à calculer sa prime.
    assert client.get(f"/api/v1/stats/equipe/{restaurant.id}", headers=auth_headers(waiter)).status_code == 403
    assert client.get(f"/api/v1/stats/equipe/{restaurant.id}").status_code == 401


def test_inverted_period_is_rejected(client, db_session):
    restaurant, _table, _item = _setup(db_session, "equipe-inverse")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = client.get(
        f"/api/v1/stats/equipe/{restaurant.id}?start=2026-08-14&end=2026-08-08",
        headers=auth_headers(manager),
    )
    assert response.status_code == 422
