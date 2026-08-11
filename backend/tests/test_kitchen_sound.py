from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_staff


def _setup_restaurant(client):
    restaurant = client.post(
        "/api/v1/restaurants", json={"name": "Café Bip", "slug": "cafe-bip"}
    ).json()
    headers = auth_headers(create_staff(restaurant["id"]))
    return restaurant, headers


def test_restaurant_starts_with_kitchen_sound_disabled(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Resto Test", "slug": "resto-sound-default"}).json()
    assert restaurant["kitchen_sound_enabled"] is False


def test_manager_can_enable_kitchen_sound(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant['id']}/kitchen-sound", json={"enabled": True}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["kitchen_sound_enabled"] is True


def test_kitchen_sound_requires_manager_role(client):
    restaurant, _headers = _setup_restaurant(client)
    waiter_headers = auth_headers(create_staff(restaurant["id"], role=StaffRole.WAITER))
    res = client.patch(
        f"/api/v1/restaurants/{restaurant['id']}/kitchen-sound", json={"enabled": True}, headers=waiter_headers
    )
    assert res.status_code == 403


def test_kitchen_sound_is_isolated_per_restaurant(client):
    restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b = client.post(
        "/api/v1/restaurants", json={"name": "Autre café bip", "slug": "autre-cafe-bip"}
    ).json()

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b['id']}/kitchen-sound", json={"enabled": True}, headers=headers_a
    )
    assert res.status_code == 403
