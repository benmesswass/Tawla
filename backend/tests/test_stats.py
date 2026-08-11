from datetime import datetime, timedelta, timezone

from app.modules.orders.models import Order, OrderStatus
from app.modules.staff.models import StaffRole
from tests.conftest import _TestingSessionLocal, auth_headers, create_staff


def _setup_restaurant(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Stats", "slug": "cafe-stats"}).json()
    manager = create_staff(restaurant["id"], role=StaffRole.MANAGER)
    manager_headers = auth_headers(manager)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant["id"], "name": "Couscous", "price": 20},
        headers=manager_headers,
    ).json()
    return restaurant, manager, manager_headers, table, item


def _create_order(client, restaurant, table, item, quantity=1):
    return client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": item["id"], "quantity": quantity}],
        },
    ).json()


def _set_order_timestamps(order_id: int, **timestamps):
    """Manipulation directe en base pour obtenir des écarts de temps déterministes
    (le lifecycle réel via l'API est trop rapide pour produire des moyennes utiles)."""
    db = _TestingSessionLocal()
    order = db.get(Order, order_id)
    for field, value in timestamps.items():
        setattr(order, field, value)
    db.commit()
    db.close()


def test_dashboard_stats_computes_timing_averages(client):
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)

    now = datetime.now(timezone.utc)
    _set_order_timestamps(
        order["id"],
        created_at=now,
        confirmed_at=now + timedelta(seconds=60),
        sent_to_kitchen_at=now + timedelta(seconds=90),
        served_at=now + timedelta(seconds=690),
        status=OrderStatus.SERVED,
    )

    res = client.get(f"/api/v1/stats/dashboard/{restaurant['id']}", headers=headers)
    assert res.status_code == 200
    timing = res.json()["timing"]
    assert timing["avg_wait_confirmation_seconds"] == 60
    assert timing["avg_confirmation_to_kitchen_seconds"] == 30
    assert timing["avg_kitchen_to_served_seconds"] == 600


def test_dashboard_stats_counts_orders_per_staff(client):
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    sami = create_staff(restaurant["id"], role=StaffRole.WAITER)
    yosra = create_staff(restaurant["id"], role=StaffRole.WAITER)

    order_1 = _create_order(client, restaurant, table, item)
    order_2 = _create_order(client, restaurant, table, item)
    order_3 = _create_order(client, restaurant, table, item)

    client.post(f"/api/v1/orders/{order_1['id']}/claim", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order_2['id']}/claim", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order_3['id']}/claim", headers=auth_headers(yosra))

    res = client.get(f"/api/v1/stats/dashboard/{restaurant['id']}", headers=manager_headers)
    performance = {p["staff_id"]: p["orders_taken"] for p in res.json()["staff_performance"]}
    assert performance[sami.id] == 2
    assert performance[yosra.id] == 1


def test_dashboard_stats_top_items_sorted_by_quantity(client):
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    other_item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant["id"], "name": "Thé", "price": 3},
        headers=headers,
    ).json()

    _create_order(client, restaurant, table, item, quantity=3)
    client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": other_item["id"], "quantity": 1}],
        },
    )

    res = client.get(f"/api/v1/stats/dashboard/{restaurant['id']}", headers=headers)
    top_items = res.json()["top_items"]
    assert top_items[0] == {"menu_item_name": "Couscous", "quantity": 3}
    assert top_items[1] == {"menu_item_name": "Thé", "quantity": 1}


def test_dashboard_stats_excludes_orders_from_other_days(client):
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    _set_order_timestamps(order["id"], created_at=yesterday)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant['id']}", headers=headers)
    assert res.json()["orders_by_hour"] == []
    assert res.json()["top_items"] == []


def test_dashboard_stats_isolated_across_restaurants(client):
    restaurant_a, _manager_a, headers_a, table_a, item_a = _setup_restaurant(client)
    restaurant_b = client.post("/api/v1/restaurants", json={"name": "Café B Stats", "slug": "cafe-b-stats"}).json()
    manager_b = create_staff(restaurant_b["id"], role=StaffRole.MANAGER)
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant_b["id"], "label": "Table 1"}, headers=auth_headers(manager_b)
    ).json()
    item_b = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant_b["id"], "name": "Pizza", "price": 15},
        headers=auth_headers(manager_b),
    ).json()
    _create_order(client, restaurant_b, table_b, item_b)

    _create_order(client, restaurant_a, table_a, item_a)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant_a['id']}", headers=headers_a)
    assert res.json()["top_items"] == [{"menu_item_name": "Couscous", "quantity": 1}]


def test_dashboard_stats_forbidden_for_other_restaurant(client):
    restaurant_a, _manager_a, headers_a, _table, _item = _setup_restaurant(client)
    restaurant_b = client.post("/api/v1/restaurants", json={"name": "Café C Stats", "slug": "cafe-c-stats"}).json()

    res = client.get(f"/api/v1/stats/dashboard/{restaurant_b['id']}", headers=headers_a)
    assert res.status_code == 403


def test_dashboard_stats_requires_manager_role(client):
    restaurant, _manager, _headers, _table, _item = _setup_restaurant(client)
    waiter = create_staff(restaurant["id"], role=StaffRole.WAITER)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant['id']}", headers=auth_headers(waiter))
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "FORBIDDEN"


def test_kitchen_today_count_counts_orders_sent_to_kitchen_today(client):
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    kitchen = create_staff(restaurant["id"], role=StaffRole.KITCHEN)

    order_1 = _create_order(client, restaurant, table, item)
    order_2 = _create_order(client, restaurant, table, item)
    _set_order_timestamps(order_1["id"], sent_to_kitchen_at=datetime.now(timezone.utc))
    _set_order_timestamps(order_2["id"], sent_to_kitchen_at=datetime.now(timezone.utc))

    # Pas encore envoyée en cuisine — ne doit pas compter.
    _create_order(client, restaurant, table, item)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant['id']}", headers=auth_headers(kitchen))
    assert res.status_code == 200
    assert res.json()["count"] == 2

    res_manager = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant['id']}", headers=manager_headers)
    assert res_manager.status_code == 200
    assert res_manager.json()["count"] == 2


def test_kitchen_today_count_excludes_yesterday(client):
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    _set_order_timestamps(order["id"], sent_to_kitchen_at=yesterday)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant['id']}", headers=manager_headers)
    assert res.json()["count"] == 0


def test_kitchen_today_count_forbidden_for_waiter(client):
    restaurant, _manager, _headers, _table, _item = _setup_restaurant(client)
    waiter = create_staff(restaurant["id"], role=StaffRole.WAITER)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant['id']}", headers=auth_headers(waiter))
    assert res.status_code == 403


def test_kitchen_today_count_forbidden_for_other_restaurant(client):
    restaurant_a, _manager_a, _headers_a, _table, _item = _setup_restaurant(client)
    restaurant_b = client.post("/api/v1/restaurants", json={"name": "Café D Stats", "slug": "cafe-d-stats"}).json()
    kitchen_a = create_staff(restaurant_a["id"], role=StaffRole.KITCHEN)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant_b['id']}", headers=auth_headers(kitchen_a))
    assert res.status_code == 403
