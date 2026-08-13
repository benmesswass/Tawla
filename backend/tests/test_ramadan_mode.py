from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_item(client):
    restaurant = create_restaurant(name="Dar Chaabane", slug="dar-chaabane-ramadan")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Chorba", "category": "Ftour", "price": 5.0},
        headers=headers,
    ).json()
    return restaurant, table, item, headers


def test_restaurant_starts_with_ramadan_mode_disabled(client):
    restaurant = create_restaurant(name="Café Test", slug="cafe-ramadan-default")
    assert restaurant.ramadan_mode_enabled is False
    assert restaurant.iftar_time is None


def test_manager_can_enable_ramadan_mode(client):
    restaurant, _table, _item, headers = _setup_restaurant_with_item(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/ramadan-mode",
        json={"enabled": True, "iftar_time": "2026-03-15T19:47:00Z"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ramadan_mode_enabled"] is True
    assert body["iftar_time"] is not None


def test_ramadan_mode_requires_manager_role(client):
    restaurant, _table, _item, _headers = _setup_restaurant_with_item(client)
    waiter_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.WAITER))
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/ramadan-mode",
        json={"enabled": True, "iftar_time": "2026-03-15T19:47:00Z"},
        headers=waiter_headers,
    )
    assert res.status_code == 403


def test_ramadan_mode_is_isolated_per_restaurant(client):
    """Un manager ne doit jamais pouvoir régler le mode Ramadan d'un autre resto."""
    restaurant_a, _table, _item, headers_a = _setup_restaurant_with_item(client)
    restaurant_b = create_restaurant(name="Autre resto", slug="autre-resto-ramadan")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b.id}/ramadan-mode",
        json={"enabled": True, "iftar_time": "2026-03-15T19:47:00Z"},
        headers=headers_a,
    )
    assert res.status_code == 403


def test_client_can_place_a_scheduled_pre_order_for_iftar(client):
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    client.patch(
        f"/api/v1/restaurants/{restaurant.id}/ramadan-mode",
        json={"enabled": True, "iftar_time": "2026-03-15T19:47:00Z"},
        headers=headers,
    )

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 2}],
            "scheduled_for": "2026-03-15T19:47:00Z",
        },
    ).json()
    assert order["scheduled_for"] is not None
    assert order["status"] == "pending_confirmation"


def test_normal_order_has_no_scheduled_for(client):
    """Une commande classique (hors pré-commande) ne doit rien avoir en scheduled_for."""
    restaurant, table, item, _headers = _setup_restaurant_with_item(client)
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    ).json()
    assert order["scheduled_for"] is None
