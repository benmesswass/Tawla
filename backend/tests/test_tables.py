import uuid

from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    slug = f"cafe-zones-{uuid.uuid4().hex[:8]}"
    restaurant = create_restaurant(name="Café Zones", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def test_create_table_with_zone(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1", "zone": "Terrasse"}, headers=headers
    )
    assert res.status_code == 201
    assert res.json()["zone"] == "Terrasse"


def test_create_table_without_zone_defaults_to_none(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    )
    assert res.status_code == 201
    assert res.json()["zone"] is None


def test_list_tables_for_restaurant(client):
    restaurant, headers = _setup_restaurant(client)
    client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1", "zone": "Plage"}, headers=headers
    )
    client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 2", "zone": "Intérieur"}, headers=headers
    )

    res = client.get(f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=headers)
    assert res.status_code == 200
    labels = {t["label"] for t in res.json()}
    assert labels == {"Table 1", "Table 2"}


def test_list_tables_requires_manager_role(client):
    restaurant, headers = _setup_restaurant(client)
    waiter = create_staff(restaurant.id, role=StaffRole.WAITER)
    res = client.get(f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=auth_headers(waiter))
    assert res.status_code == 403


def test_list_tables_is_isolated_per_restaurant(client):
    restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Autre Café", slug="autre-cafe")
    headers_b = auth_headers(create_staff(restaurant_b.id))

    client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant_a.id, "label": "Table A", "zone": "Plage"}, headers=headers_a
    )
    client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant_b.id, "label": "Table B"}, headers=headers_b
    )

    res = client.get(f"/api/v1/tables/by-restaurant/{restaurant_a.id}", headers=headers_a)
    labels = [t["label"] for t in res.json()]
    assert labels == ["Table A"]

    res_forbidden = client.get(f"/api/v1/tables/by-restaurant/{restaurant_b.id}", headers=headers_a)
    assert res_forbidden.status_code == 403


def test_update_table_label_and_zone(client):
    restaurant, headers = _setup_restaurant(client)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()

    res = client.patch(
        f"/api/v1/tables/{table['id']}", json={"label": "Table 1 bis", "zone": "Terrasse"}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["label"] == "Table 1 bis"
    assert res.json()["zone"] == "Terrasse"


def test_update_table_can_clear_zone(client):
    restaurant, headers = _setup_restaurant(client)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1", "zone": "Plage"}, headers=headers
    ).json()

    res = client.patch(f"/api/v1/tables/{table['id']}", json={"label": "Table 1", "zone": None}, headers=headers)
    assert res.status_code == 200
    assert res.json()["zone"] is None


def test_update_table_from_another_restaurant_is_not_found(client):
    _restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b, headers_b = _setup_restaurant(client)
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant_b.id, "label": "Table B"}, headers=headers_b
    ).json()

    res = client.patch(f"/api/v1/tables/{table_b['id']}", json={"label": "Hack", "zone": "Plage"}, headers=headers_a)
    assert res.status_code == 404


def test_get_table_poster_returns_a_pdf(client):
    restaurant, headers = _setup_restaurant(client)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()

    res = client.get(f"/api/v1/tables/{table['id']}/poster", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")


def test_get_table_poster_requires_manager_role(client):
    restaurant, headers = _setup_restaurant(client)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    waiter = create_staff(restaurant.id, role=StaffRole.WAITER)

    res = client.get(f"/api/v1/tables/{table['id']}/poster", headers=auth_headers(waiter))
    assert res.status_code == 403


def test_get_table_poster_from_another_restaurant_is_not_found(client):
    _restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b, headers_b = _setup_restaurant(client)
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant_b.id, "label": "Table B"}, headers=headers_b
    ).json()

    res = client.get(f"/api/v1/tables/{table_b['id']}/poster", headers=headers_a)
    assert res.status_code == 404
