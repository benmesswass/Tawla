"""
Les trois métriques de preuve (Phase 13.3).

Ce sont les chiffres que Wassim montrera à un patron à la fin d'un pilote, et
au jury. Ils doivent donc être justes au sens métier, pas seulement calculés :
une annulation ne doit pas passer pour un panier, une commande encore en
attente ne doit jamais compter comme perdue (elle peut toujours aboutir,
décision du 2026-08-28), et la période de comparaison doit avoir la même
longueur que la période mesurée.
"""
from datetime import date, datetime, timedelta, timezone

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
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


def _add_order(
    db_session,
    restaurant,
    table,
    item,
    *,
    created_at: datetime,
    status: OrderStatus = OrderStatus.SERVED,
    sent_to_kitchen_after: timedelta | None = None,
    quantity: int = 1,
    unit_price: float = 20.0,
    payment_status: PaymentStatus = PaymentStatus.PAID,
) -> Order:
    """Écrit une commande directement en base : les horodatages passés ne sont
    pas atteignables par l'API, et c'est précisément ce qu'on veut mesurer.

    `payment_status` vaut PAID par défaut : le panier moyen ne se calcule que
    sur les commandes réglées, une commande impayée n'étant pas un panier."""
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=status,
        payment_status=payment_status,
        created_at=created_at,
        sent_to_kitchen_at=created_at + sent_to_kitchen_after if sent_to_kitchen_after else None,
    )
    order.items.append(
        OrderItem(
            menu_item_id=item.id,
            menu_item_name=item.name,
            unit_price=unit_price,
            quantity=quantity,
        )
    )
    db_session.add(order)
    db_session.commit()
    return order


def _proof(client, restaurant, manager, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"/api/v1/stats/preuve/{restaurant.id}" + (f"?{query}" if query else "")
    response = client.get(url, headers=auth_headers(manager))
    assert response.status_code == 200, response.text
    return response.json()


def test_counts_orders_and_average_basket_over_the_period(client, db_session):
    restaurant, table, item = _setup(db_session, "preuve-panier")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    now = datetime.now(timezone.utc)

    _add_order(db_session, restaurant, table, item, created_at=now - timedelta(hours=2), quantity=1)
    _add_order(db_session, restaurant, table, item, created_at=now - timedelta(hours=3), quantity=3)

    current = _proof(client, restaurant, manager)["current"]
    assert current["orders_count"] == 2
    # (20 + 60) / 2
    assert current["avg_basket_amount"] == 40.0


def test_cancelled_order_is_lost_and_excluded_from_the_basket(client, db_session):
    """Une commande annulée n'a jamais été un panier : la compter tirerait la
    moyenne vers le bas sans rien dire du service."""
    restaurant, table, item = _setup(db_session, "preuve-annulee")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    now = datetime.now(timezone.utc)

    _add_order(db_session, restaurant, table, item, created_at=now - timedelta(hours=1), quantity=1)
    _add_order(
        db_session, restaurant, table, item,
        created_at=now - timedelta(hours=1), status=OrderStatus.CANCELLED, quantity=10,
    )

    current = _proof(client, restaurant, manager)["current"]
    assert current["orders_count"] == 2
    assert current["cancelled_orders_count"] == 1
    assert current["avg_basket_amount"] == 20.0  # la commande annulée est exclue


def test_order_left_pending_indefinitely_does_not_count_as_lost(client, db_session):
    """
    Décision de Wassim (2026-08-28) : une commande jamais prise en charge peut
    toujours l'être, contrairement à une annulation — la compter comme perdue
    confondait une vente lente avec une vente ratée. Peu importe son âge, elle
    ne doit jamais entrer dans `cancelled_orders_count`.
    """
    restaurant, table, item = _setup(db_session, "preuve-oubliee")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    now = datetime.now(timezone.utc)

    _add_order(
        db_session, restaurant, table, item,
        created_at=now - timedelta(hours=1), status=OrderStatus.PENDING_CONFIRMATION,
    )
    _add_order(
        db_session, restaurant, table, item,
        created_at=now - timedelta(minutes=2), status=OrderStatus.PENDING_CONFIRMATION,
    )

    current = _proof(client, restaurant, manager)["current"]
    assert current["orders_count"] == 2
    assert current["cancelled_orders_count"] == 0


def test_average_delay_from_order_to_kitchen(client, db_session):
    restaurant, table, item = _setup(db_session, "preuve-delai")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    now = datetime.now(timezone.utc)

    _add_order(
        db_session, restaurant, table, item,
        created_at=now - timedelta(hours=2), sent_to_kitchen_after=timedelta(minutes=4),
    )
    _add_order(
        db_session, restaurant, table, item,
        created_at=now - timedelta(hours=3), sent_to_kitchen_after=timedelta(minutes=6),
    )
    # Jamais partie en cuisine : ne doit pas être comptée dans la moyenne.
    _add_order(
        db_session, restaurant, table, item,
        created_at=now - timedelta(hours=4), status=OrderStatus.PENDING_CONFIRMATION,
    )

    current = _proof(client, restaurant, manager)["current"]
    assert current["avg_order_to_kitchen_seconds"] == 300.0  # (240 + 360) / 2


def test_previous_period_has_the_same_length_and_precedes_the_current_one(client, db_session):
    restaurant, _, _ = _setup(db_session, "preuve-periode")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    body = _proof(client, restaurant, manager, start="2026-08-08", end="2026-08-14")
    assert body["current"]["start"] == "2026-08-08"
    assert body["current"]["end"] == "2026-08-14"
    # 7 jours demandés -> les 7 jours juste avant.
    assert body["previous"]["start"] == "2026-08-01"
    assert body["previous"]["end"] == "2026-08-07"


def test_orders_are_attributed_to_the_right_period(client, db_session):
    restaurant, table, item = _setup(db_session, "preuve-decoupage")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    def at(day: str) -> datetime:
        return datetime.combine(date.fromisoformat(day), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)

    _add_order(db_session, restaurant, table, item, created_at=at("2026-08-10"))  # période courante
    _add_order(db_session, restaurant, table, item, created_at=at("2026-08-14"))  # dernier jour inclus
    _add_order(db_session, restaurant, table, item, created_at=at("2026-08-03"))  # période précédente
    _add_order(db_session, restaurant, table, item, created_at=at("2026-07-20"))  # hors des deux

    body = _proof(client, restaurant, manager, start="2026-08-08", end="2026-08-14")
    assert body["current"]["orders_count"] == 2
    assert body["previous"]["orders_count"] == 1


def test_default_period_is_the_last_seven_days(client, db_session):
    restaurant, table, item = _setup(db_session, "preuve-defaut")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    now = datetime.now(timezone.utc)

    _add_order(db_session, restaurant, table, item, created_at=now - timedelta(days=2))
    _add_order(db_session, restaurant, table, item, created_at=now - timedelta(days=9))

    body = _proof(client, restaurant, manager)
    assert body["current"]["orders_count"] == 1
    assert body["previous"]["orders_count"] == 1
    assert (date.fromisoformat(body["current"]["end"]) - date.fromisoformat(body["current"]["start"])).days == 6


def test_empty_period_returns_nulls_not_zeros(client, db_session):
    """Zéro dinar de panier moyen et « aucune donnée » ne veulent pas dire la
    même chose devant un patron."""
    restaurant, _, _ = _setup(db_session, "preuve-vide")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    current = _proof(client, restaurant, manager)["current"]
    assert current["orders_count"] == 0
    assert current["avg_basket_amount"] is None
    assert current["avg_order_to_kitchen_seconds"] is None


def test_proof_is_isolated_between_restaurants(client, db_session):
    restaurant, table, item = _setup(db_session, "preuve-iso-a")
    other, other_table, other_item = _setup(db_session, "preuve-iso-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    now = datetime.now(timezone.utc)

    _add_order(db_session, restaurant, table, item, created_at=now - timedelta(hours=1))
    _add_order(db_session, other, other_table, other_item, created_at=now - timedelta(hours=1))
    _add_order(db_session, other, other_table, other_item, created_at=now - timedelta(hours=2))

    assert _proof(client, restaurant, manager)["current"]["orders_count"] == 1

    forbidden = client.get(f"/api/v1/stats/preuve/{other.id}", headers=auth_headers(manager))
    assert forbidden.status_code == 403


def test_proof_is_manager_only(client, db_session):
    restaurant, _, _ = _setup(db_session, "preuve-role")
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)

    assert client.get(f"/api/v1/stats/preuve/{restaurant.id}").status_code == 401
    for staff in (waiter, kitchen):
        response = client.get(f"/api/v1/stats/preuve/{restaurant.id}", headers=auth_headers(staff))
        assert response.status_code == 403


def test_inverted_period_is_rejected(client, db_session):
    restaurant, _, _ = _setup(db_session, "preuve-inverse")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}?start=2026-08-14&end=2026-08-08",
        headers=auth_headers(manager),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_PERIOD"
