from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    restaurant = create_restaurant(name="Café du Coin", slug="cafe-du-coin")
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def test_restaurant_starts_with_cafe_mode_disabled(client):
    restaurant = create_restaurant(name="Resto Test", slug="resto-cafe-default")
    assert restaurant.cafe_mode_enabled is False


def test_manager_can_enable_cafe_mode(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/cafe-mode", json={"enabled": True}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["cafe_mode_enabled"] is True


def test_cafe_mode_requires_manager_role(client):
    restaurant, _headers = _setup_restaurant(client)
    waiter_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.WAITER))
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/cafe-mode", json={"enabled": True}, headers=waiter_headers
    )
    assert res.status_code == 403


def test_cafe_mode_is_isolated_per_restaurant(client):
    restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Autre café", slug="autre-cafe")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b.id}/cafe-mode", json={"enabled": True}, headers=headers_a
    )
    assert res.status_code == 403
