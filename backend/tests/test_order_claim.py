from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_pending_order(client):
    restaurant = create_restaurant(name="Café Claim", slug="cafe-claim")
    manager_headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Thé à la menthe", "price": 3},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"]}]},
    ).json()
    return restaurant, order


def test_claim_assigns_order_to_staff(client):
    restaurant, order = _setup_pending_order(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)

    res = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))
    assert res.status_code == 200
    body = res.json()
    assert body["taken_by_staff_id"] == sami.id
    assert body["taken_by_staff_name"] == sami.name


def test_cannot_claim_order_already_claimed_by_another_staff(client):
    restaurant, order = _setup_pending_order(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)
    yosra = create_staff(restaurant.id, role=StaffRole.WAITER)

    client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))
    res = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(yosra))

    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ALREADY_CLAIMED"


def test_claiming_twice_by_the_same_staff_is_not_an_error(client):
    restaurant, order = _setup_pending_order(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)

    first = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))
    second = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))

    assert first.status_code == 200
    assert second.status_code == 200


def test_cannot_claim_an_already_confirmed_order(client):
    restaurant, order = _setup_pending_order(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)

    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(sami))
    res = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))

    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_confirm_without_prior_claim_auto_assigns_the_confirming_staff(client):
    """
    Un serveur qui confirme directement (sans passer par le bouton "prendre
    en charge") doit quand même apparaître dans les stats — sinon les
    commandes confirmées d'un coup échappent au comptage par serveur.
    """
    restaurant, order = _setup_pending_order(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)

    res = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(sami))
    assert res.status_code == 200
    assert res.json()["taken_by_staff_id"] == sami.id


def test_claim_is_isolated_across_restaurants(client):
    _restaurant_a, order = _setup_pending_order(client)
    other_restaurant = create_restaurant(name="Autre Café", slug="autre-cafe")
    staff_b = create_staff(other_restaurant.id, role=StaffRole.WAITER)

    res = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(staff_b))
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_kitchen_staff_cannot_claim_orders(client):
    restaurant, order = _setup_pending_order(client)
    kitchen = create_staff(restaurant.id, role=StaffRole.KITCHEN)

    res = client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(kitchen))
    assert res.status_code == 403
