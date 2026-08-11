from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_staff


def _setup_order(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Paiement", "slug": "cafe-paiement"}).json()
    manager_headers = auth_headers(create_staff(restaurant["id"]))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant["id"], "name": "Couscous", "price": 20},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 2}],
        },
    ).json()
    return restaurant, manager_headers, order


def test_pay_by_card_covers_full_amount_plus_tip(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["payment_method"] == "card"
    assert body["payment_status"] == "paid"
    assert body["tip_amount"] == 5
    assert body["total_amount"] == 40  # 2 x 20 DT, hors pourboire


def test_pay_by_card_defaults_to_no_tip(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={})
    assert res.status_code == 200
    assert res.json()["tip_amount"] == 0


def test_pay_by_card_rejects_negative_tip(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": -5})
    assert res.status_code == 422


def test_cannot_pay_twice(client):
    _restaurant, _headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0})

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ALREADY_PAID"


def test_request_cash_payment_notifies_staff_and_is_confirmable(client):
    restaurant, manager_headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/cash")
    assert res.status_code == 200
    assert res.json()["payment_status"] == "pending"
    assert res.json()["payment_method"] == "cash"

    pending = client.get(f"/api/v1/orders/by-restaurant/{restaurant['id']}/pending-cash-payments", headers=manager_headers)
    assert [o["id"] for o in pending.json()] == [order["id"]]

    confirmed = client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["payment_status"] == "paid"

    pending_after = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant['id']}/pending-cash-payments", headers=manager_headers
    )
    assert pending_after.json() == []


def test_pending_cash_payment_carries_the_dedicated_server_id(client):
    """
    Le frontend n'affiche la demande de paiement qu'au serveur qui a pris en
    charge la table (le manager voit tout) — ça suppose que taken_by_staff_id
    est bien porté par la liste des demandes en attente.
    """
    restaurant, manager_headers, order = _setup_order(client)
    sami = create_staff(restaurant["id"], role=StaffRole.WAITER)

    client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order['id']}/pay/cash")

    pending = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant['id']}/pending-cash-payments", headers=manager_headers
    )
    assert pending.json()[0]["taken_by_staff_id"] == sami.id


def test_pending_cash_payments_survives_order_being_served(client):
    """
    Le paiement cash arrive souvent après "servie" — l'endpoint dédié ne doit
    pas dépendre de ACTIVE_STATUSES (qui exclut "served").
    """
    restaurant, manager_headers, order = _setup_order(client)
    sami = create_staff(restaurant["id"], role=StaffRole.WAITER)
    karim = create_staff(restaurant["id"], role=StaffRole.KITCHEN)
    headers = auth_headers(sami)

    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers)
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=headers)
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=auth_headers(karim))
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=auth_headers(karim))
    client.post(f"/api/v1/orders/{order['id']}/mark-served", headers=headers)

    client.post(f"/api/v1/orders/{order['id']}/pay/cash")

    pending = client.get(f"/api/v1/orders/by-restaurant/{restaurant['id']}/pending-cash-payments", headers=manager_headers)
    assert [o["id"] for o in pending.json()] == [order["id"]]


def test_confirm_cash_payment_rejects_when_no_pending_request(client):
    _restaurant, manager_headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "NO_PENDING_CASH_PAYMENT"


def test_cannot_pay_a_cancelled_order(client):
    _restaurant, headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ORDER_CANCELLED"


def test_pending_cash_payments_isolated_across_restaurants(client):
    restaurant_a, manager_headers_a, order_a = _setup_order(client)
    restaurant_b = client.post("/api/v1/restaurants", json={"name": "Café B Paiement", "slug": "cafe-b-paiement"}).json()
    manager_b = create_staff(restaurant_b["id"], role=StaffRole.MANAGER)

    client.post(f"/api/v1/orders/{order_a['id']}/pay/cash")

    res = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant_b['id']}/pending-cash-payments", headers=auth_headers(manager_b)
    )
    assert res.json() == []


def test_pay_by_card_is_public_no_auth_required(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0})
    assert res.status_code == 200
