from datetime import datetime, time, timedelta, timezone

from app.modules.orders.models import Order, OrderStatus
from app.modules.staff.models import StaffRole
from tests.conftest import _TestingSessionLocal, auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    restaurant = create_restaurant(name="Café Stats", slug="cafe-stats")
    manager = create_staff(restaurant.id, role=StaffRole.MANAGER)
    manager_headers = auth_headers(manager)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 20},
        headers=manager_headers,
    ).json()
    return restaurant, manager, manager_headers, table, item


def _create_order(client, restaurant, table, item, quantity=1):
    return client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
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
        paid_at=now + timedelta(seconds=1090),
        status=OrderStatus.SERVED,
    )

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers)
    assert res.status_code == 200
    timing = res.json()["timing"]
    assert timing["avg_wait_confirmation_seconds"] == 60
    assert timing["avg_confirmation_to_kitchen_seconds"] == 30
    assert timing["avg_kitchen_to_served_seconds"] == 600
    assert timing["avg_served_to_paid_seconds"] == 400


def test_dashboard_stats_counts_orders_per_staff(client):
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)
    yosra = create_staff(restaurant.id, role=StaffRole.WAITER)

    order_1 = _create_order(client, restaurant, table, item)
    order_2 = _create_order(client, restaurant, table, item)
    order_3 = _create_order(client, restaurant, table, item)

    client.post(f"/api/v1/orders/{order_1['id']}/claim", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order_2['id']}/claim", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order_3['id']}/claim", headers=auth_headers(yosra))

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=manager_headers)
    performance = {p["staff_id"]: p["orders_taken"] for p in res.json()["staff_performance"]}
    assert performance[sami.id] == 2
    assert performance[yosra.id] == 1


def test_dashboard_stats_lists_a_waiter_with_zero_orders(client):
    """
    Un serveur présent mais qui n'a encore rien pris en charge disparaissait du
    rapport au lieu d'y apparaître à 0 : le manager ne pouvait pas distinguer
    "absent aujourd'hui" de "présent, zéro commande" (retour démo 2026-08-31).
    """
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)
    idle_waiter = create_staff(restaurant.id, role=StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, role=StaffRole.KITCHEN)

    order = _create_order(client, restaurant, table, item)
    client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=manager_headers)
    performance = {p["staff_id"]: p["orders_taken"] for p in res.json()["staff_performance"]}
    assert performance[sami.id] == 1
    assert performance[idle_waiter.id] == 0
    # Un compte cuisine ne peut jamais prendre de commande : il n'a rien à
    # faire dans un rapport "commandes par serveur", pas même à 0.
    assert kitchen.id not in performance


def test_dashboard_stats_excludes_inactive_staff_with_no_orders(client):
    """Un compte désactivé sans commande sur la journée n'a rien à montrer."""
    restaurant, _manager, manager_headers, _table, _item = _setup_restaurant(client)
    inactive = create_staff(restaurant.id, role=StaffRole.WAITER)
    inactive.is_active = False
    db = _TestingSessionLocal()
    db.merge(inactive)
    db.commit()
    db.close()

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=manager_headers)
    performance = {p["staff_id"]: p["orders_taken"] for p in res.json()["staff_performance"]}
    assert inactive.id not in performance


def test_team_report_lists_a_waiter_with_zero_orders(client):
    """Même bug, même correctif, côté rapport d'équipe (période) plutôt que dashboard du jour."""
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)
    idle_waiter = create_staff(restaurant.id, role=StaffRole.WAITER)

    order = _create_order(client, restaurant, table, item)
    client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))

    today = datetime.now(timezone.utc).date().isoformat()
    res = client.get(
        f"/api/v1/stats/equipe/{restaurant.id}", params={"start": today, "end": today}, headers=manager_headers
    )
    assert res.status_code == 200
    rows = {row["staff_id"]: row["orders_taken"] for row in res.json()["staff"]}
    assert rows[sami.id] == 1
    assert rows[idle_waiter.id] == 0


def test_team_report_is_not_empty_when_a_waiter_has_not_taken_an_order(client):
    """
    L'ancien code renvoyait une liste vide dès qu'aucun serveur n'avait pris de
    commande sur la période, même avec un serveur actif présent — la période
    correspondante n'existait donc pour personne dans le rapport. Le manager
    (créé par _setup_restaurant) n'a pas à apparaître : il n'a rien pris, et ce
    rapport suit les serveurs (test_team_report.py couvre déjà ce choix).
    """
    restaurant, _manager, manager_headers, _table, _item = _setup_restaurant(client)
    waiter = create_staff(restaurant.id, role=StaffRole.WAITER)

    today = datetime.now(timezone.utc).date().isoformat()
    res = client.get(
        f"/api/v1/stats/equipe/{restaurant.id}", params={"start": today, "end": today}, headers=manager_headers
    )
    assert res.status_code == 200
    rows = {row["staff_id"]: row["orders_taken"] for row in res.json()["staff"]}
    assert rows == {waiter.id: 0}


def test_dashboard_stats_top_items_sorted_by_quantity(client):
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    other_item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Thé", "price": 3},
        headers=headers,
    ).json()

    _create_order(client, restaurant, table, item, quantity=3)
    client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": other_item["id"], "quantity": 1}],
        },
    )

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers)
    top_items = res.json()["top_items"]
    assert top_items[0] == {"menu_item_name": "Couscous", "quantity": 3}
    assert top_items[1] == {"menu_item_name": "Thé", "quantity": 1}


def test_dashboard_stats_excludes_orders_from_other_days(client):
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    _set_order_timestamps(order["id"], created_at=yesterday)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers)
    assert res.json()["orders_by_hour"] == []
    assert res.json()["top_items"] == []


def test_active_orders_count_excludes_orders_before_service_day(client):
    """
    F-2 : `active_orders_count` n'était borné par aucune date — une commande
    active de la veille (jamais confirmée, jamais annulée) restait comptée
    indéfiniment, contrairement à `list_active_orders` que l'écran serveur
    affiche (bornée par `service_day_start()` depuis la Phase 19.5). Le
    manager voyait donc un nombre que l'écran serveur ne montrait plus.
    """
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)

    before_service_day = datetime.now(timezone.utc) - timedelta(days=2)
    _set_order_timestamps(order["id"], created_at=before_service_day)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=headers)
    assert res.json()["active_orders_count"] == 0


def test_dashboard_stats_attribue_une_commande_de_sohour_a_la_veille(client):
    """
    F-3 : les stats coupaient à minuit UTC, les écrans de service à 5h Tunis
    (Phase 19.5). Une commande passée à 2h UTC (3h Tunis) — le sohour d'un
    Ramadan — appartient encore au service de la veille pour les écrans, mais
    tombait sous "aujourd'hui" dans les stats : le manager et le serveur ne
    parlaient pas du même jour.
    """
    restaurant, _manager, headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)

    aujourdhui = datetime.now(timezone.utc).date()
    sohour = datetime.combine(aujourdhui, time(hour=2), tzinfo=timezone.utc)
    _set_order_timestamps(order["id"], created_at=sohour)

    res_aujourdhui = client.get(
        f"/api/v1/stats/dashboard/{restaurant.id}", params={"date": aujourdhui.isoformat()}, headers=headers
    )
    assert res_aujourdhui.json()["top_items"] == []

    veille = aujourdhui - timedelta(days=1)
    res_veille = client.get(
        f"/api/v1/stats/dashboard/{restaurant.id}", params={"date": veille.isoformat()}, headers=headers
    )
    assert res_veille.json()["top_items"] == [{"menu_item_name": "Couscous", "quantity": 1}]


def test_dashboard_stats_isolated_across_restaurants(client):
    restaurant_a, _manager_a, headers_a, table_a, item_a = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Café B Stats", slug="cafe-b-stats")
    manager_b = create_staff(restaurant_b.id, role=StaffRole.MANAGER)
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant_b.id, "label": "Table 1"}, headers=auth_headers(manager_b)
    ).json()
    item_b = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant_b.id, "name": "Pizza", "price": 15},
        headers=auth_headers(manager_b),
    ).json()
    _create_order(client, restaurant_b, table_b, item_b)

    _create_order(client, restaurant_a, table_a, item_a)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant_a.id}", headers=headers_a)
    assert res.json()["top_items"] == [{"menu_item_name": "Couscous", "quantity": 1}]


def test_dashboard_stats_forbidden_for_other_restaurant(client):
    restaurant_a, _manager_a, headers_a, _table, _item = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Café C Stats", slug="cafe-c-stats")

    res = client.get(f"/api/v1/stats/dashboard/{restaurant_b.id}", headers=headers_a)
    assert res.status_code == 403


def test_dashboard_stats_requires_manager_role(client):
    restaurant, _manager, _headers, _table, _item = _setup_restaurant(client)
    waiter = create_staff(restaurant.id, role=StaffRole.WAITER)

    res = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(waiter))
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "FORBIDDEN"


def test_kitchen_today_count_counts_orders_sent_to_kitchen_today(client):
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    kitchen = create_staff(restaurant.id, role=StaffRole.KITCHEN)

    order_1 = _create_order(client, restaurant, table, item)
    order_2 = _create_order(client, restaurant, table, item)
    _set_order_timestamps(order_1["id"], sent_to_kitchen_at=datetime.now(timezone.utc))
    _set_order_timestamps(order_2["id"], sent_to_kitchen_at=datetime.now(timezone.utc))

    # Pas encore envoyée en cuisine — ne doit pas compter.
    _create_order(client, restaurant, table, item)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant.id}", headers=auth_headers(kitchen))
    assert res.status_code == 200
    assert res.json()["count"] == 2

    res_manager = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant.id}", headers=manager_headers)
    assert res_manager.status_code == 200
    assert res_manager.json()["count"] == 2


def test_kitchen_today_count_excludes_yesterday(client):
    restaurant, _manager, manager_headers, table, item = _setup_restaurant(client)
    order = _create_order(client, restaurant, table, item)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    _set_order_timestamps(order["id"], sent_to_kitchen_at=yesterday)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant.id}", headers=manager_headers)
    assert res.json()["count"] == 0


def test_kitchen_today_count_forbidden_for_waiter(client):
    restaurant, _manager, _headers, _table, _item = _setup_restaurant(client)
    waiter = create_staff(restaurant.id, role=StaffRole.WAITER)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant.id}", headers=auth_headers(waiter))
    assert res.status_code == 403


def test_kitchen_today_count_forbidden_for_other_restaurant(client):
    restaurant_a, _manager_a, _headers_a, _table, _item = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Café D Stats", slug="cafe-d-stats")
    kitchen_a = create_staff(restaurant_a.id, role=StaffRole.KITCHEN)

    res = client.get(f"/api/v1/stats/kitchen-today-count/{restaurant_b.id}", headers=auth_headers(kitchen_a))
    assert res.status_code == 403
