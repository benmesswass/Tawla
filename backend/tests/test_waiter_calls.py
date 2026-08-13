import uuid

from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_table(client):
    slug = f"dar-chaabane-calls-{uuid.uuid4().hex[:8]}"
    restaurant = create_restaurant(name="Dar Chaabane", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    return restaurant, table, headers


def test_client_can_call_waiter(client):
    restaurant, table, _headers = _setup_restaurant_with_table(client)
    res = client.post("/api/v1/waiter-calls", json={"qr_token": table["qr_token"]})
    assert res.status_code == 201
    body = res.json()
    assert body["resolved_at"] is None
    assert body["table_id"] == table["id"]


def test_a_call_always_belongs_to_the_restaurant_of_its_table(client):
    """Le restaurant n'est plus reçu du client mais déduit de la table : viser
    un autre établissement est devenu impossible par construction, là où il
    suffisait avant d'envoyer un autre `restaurant_id`."""
    _restaurant_a, _table_a, _headers = _setup_restaurant_with_table(client)
    restaurant_b, table_b, _headers_b = _setup_restaurant_with_table(client)

    body = client.post("/api/v1/waiter-calls", json={"qr_token": table_b["qr_token"]}).json()

    assert body["restaurant_id"] == restaurant_b.id
    assert body["table_id"] == table_b["id"]


def test_staff_sees_pending_call_and_can_resolve_it(client):
    restaurant, table, headers = _setup_restaurant_with_table(client)
    call = client.post(
        "/api/v1/waiter-calls", json={"qr_token": table["qr_token"]}
    ).json()

    pending = client.get(f"/api/v1/waiter-calls/by-restaurant/{restaurant.id}/pending", headers=headers).json()
    assert len(pending) == 1
    assert pending[0]["id"] == call["id"]

    resolved = client.post(f"/api/v1/waiter-calls/{call['id']}/resolve", headers=headers).json()
    assert resolved["resolved_at"] is not None
    assert resolved["resolved_by_staff_id"] is not None

    pending_after = client.get(
        f"/api/v1/waiter-calls/by-restaurant/{restaurant.id}/pending", headers=headers
    ).json()
    assert pending_after == []


def test_cannot_resolve_already_resolved_call(client):
    restaurant, table, headers = _setup_restaurant_with_table(client)
    call = client.post(
        "/api/v1/waiter-calls", json={"qr_token": table["qr_token"]}
    ).json()
    client.post(f"/api/v1/waiter-calls/{call['id']}/resolve", headers=headers)

    res = client.post(f"/api/v1/waiter-calls/{call['id']}/resolve", headers=headers)
    assert res.status_code == 409


def test_pending_calls_isolated_per_restaurant(client):
    restaurant_a, table_a, headers_a = _setup_restaurant_with_table(client)
    restaurant_b, table_b, headers_b = _setup_restaurant_with_table(client)

    client.post("/api/v1/waiter-calls", json={"qr_token": table_a["qr_token"]})
    client.post("/api/v1/waiter-calls", json={"qr_token": table_b["qr_token"]})

    pending_a = client.get(f"/api/v1/waiter-calls/by-restaurant/{restaurant_a.id}/pending", headers=headers_a).json()
    assert len(pending_a) == 1
    assert pending_a[0]["table_id"] == table_a["id"]

    res = client.get(f"/api/v1/waiter-calls/by-restaurant/{restaurant_b.id}/pending", headers=headers_a)
    assert res.status_code == 403
