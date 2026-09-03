from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    restaurant = create_restaurant(name="Dar Chaabane", slug="dar-chaabane-legal")
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def _payload(**overrides):
    base = {"legal_address": None, "tax_id": None, "vat_number": None}
    base.update(overrides)
    return base


def test_manager_can_set_legal_info(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json=_payload(
            legal_address="12 rue de la République, 75011 Paris",
            tax_id="812 345 678 00019",
            vat_number="FR32812345678",
        ),
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["legal_address"] == "12 rue de la République, 75011 Paris"
    assert body["tax_id"] == "812 345 678 00019"
    assert body["vat_number"] == "FR32812345678"


def test_legal_info_rejects_field_over_max_length(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json=_payload(tax_id="a" * 61),
        headers=headers,
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "FIELD_TOO_LONG"
    assert detail["field"] == "tax_id"


def test_legal_info_blank_string_clears_field(client):
    restaurant, headers = _setup_restaurant(client)
    client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json=_payload(legal_address="12 rue de la République, 75011 Paris"),
        headers=headers,
    )

    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json=_payload(legal_address="  "),
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["legal_address"] is None


def test_legal_info_requires_manager_role(client):
    restaurant, _headers = _setup_restaurant(client)
    waiter_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.WAITER))
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json=_payload(),
        headers=waiter_headers,
    )
    assert res.status_code == 403


def test_legal_info_isolated_per_restaurant(client):
    restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Autre resto", slug="autre-resto-legal")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b.id}/legal-info",
        json=_payload(legal_address="Ailleurs"),
        headers=headers_a,
    )
    assert res.status_code == 403
