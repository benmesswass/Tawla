import uuid

from app.modules.loyalty.models import LOYALTY_REWARD_THRESHOLD
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup_restaurant(client):
    slug = f"cafe-fidelite-{uuid.uuid4().hex[:8]}"
    restaurant = create_restaurant(name="Café Fidélité", slug=slug)
    manager_headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Café", "price": 3.5},
        headers=manager_headers,
    ).json()
    return restaurant, table, item, manager_headers


def _order_and_pay_by_card(client, restaurant, table, item, phone):
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "loyalty_phone": phone,
        },
    ).json()
    return client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    ).json()


def test_lookup_creates_a_new_member(client):
    restaurant, _table, _item, _headers = _setup_restaurant(client)
    res = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": "20123456"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["order_count"] == 0
    assert body["reward_available"] is False
    assert body["orders_until_reward"] == LOYALTY_REWARD_THRESHOLD


def test_lookup_is_idempotent_for_the_same_phone(client):
    restaurant, _table, _item, _headers = _setup_restaurant(client)
    payload = {"restaurant_id": restaurant.id, "phone_number": "20123456"}
    first = client.post("/api/v1/loyalty/lookup", json=payload).json()
    second = client.post("/api/v1/loyalty/lookup", json=payload).json()
    assert first["id"] == second["id"]


def test_order_count_only_increments_on_confirmed_payment(client):
    """Une commande jamais payée ne doit jamais faire gagner de point."""
    restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20123456"

    client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "loyalty_phone": phone,
        },
    )

    status = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": phone}
    ).json()
    assert status["order_count"] == 0


def test_order_count_increments_on_card_payment(client):
    restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20123456"

    order = _order_and_pay_by_card(client, restaurant, table, item, phone)
    assert order["payment_status"] == "paid"

    status = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": phone}
    ).json()
    assert status["order_count"] == 1


def test_order_count_increments_on_confirmed_cash_payment(client):
    restaurant, table, item, manager_headers = _setup_restaurant(client)
    phone = "20654321"

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "loyalty_phone": phone,
        },
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))
    # Une demande cash seule (pas encore encaissée) ne doit rien faire gagner.
    status_before = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": phone}
    ).json()
    assert status_before["order_count"] == 0

    client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    status_after = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": phone}
    ).json()
    assert status_after["order_count"] == 1


def test_reward_becomes_available_at_threshold(client):
    restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20111222"

    for _ in range(LOYALTY_REWARD_THRESHOLD):
        order = _order_and_pay_by_card(client, restaurant, table, item, phone)

    status = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": phone}
    ).json()
    assert status["order_count"] == LOYALTY_REWARD_THRESHOLD
    assert status["reward_available"] is True
    assert status["orders_until_reward"] == 0
    assert order["payment_status"] == "paid"


def test_staff_can_redeem_reward(client):
    restaurant, table, item, manager_headers = _setup_restaurant(client)
    phone = "20111222"
    for _ in range(LOYALTY_REWARD_THRESHOLD):
        _order_and_pay_by_card(client, restaurant, table, item, phone)

    member = client.get(
        f"/api/v1/loyalty/by-restaurant/{restaurant.id}/member",
        params={"phone_number": phone},
        headers=manager_headers,
    ).json()
    assert member["reward_available"] is True

    redeemed = client.post(f"/api/v1/loyalty/{member['id']}/redeem", headers=manager_headers)
    assert redeemed.status_code == 200
    assert redeemed.json()["reward_available"] is False


def test_cannot_redeem_when_no_reward_available(client):
    restaurant, _table, _item, manager_headers = _setup_restaurant(client)
    member = client.post(
        "/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": "20999888"}
    ).json()

    res = client.post(f"/api/v1/loyalty/{member['id']}/redeem", headers=manager_headers)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "NO_REWARD_AVAILABLE"


def test_staff_member_lookup_requires_role(client):
    restaurant, _table, _item, _manager_headers = _setup_restaurant(client)
    client.post("/api/v1/loyalty/lookup", json={"restaurant_id": restaurant.id, "phone_number": "20999888"})

    kitchen_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.KITCHEN))
    res = client.get(
        f"/api/v1/loyalty/by-restaurant/{restaurant.id}/member",
        params={"phone_number": "20999888"},
        headers=kitchen_headers,
    )
    assert res.status_code == 403


def test_loyalty_is_isolated_per_restaurant(client):
    restaurant_a, _table_a, _item_a, headers_a = _setup_restaurant(client)
    restaurant_b, _table_b, _item_b, _headers_b = _setup_restaurant(client)
    phone = "20111222"

    client.post("/api/v1/loyalty/lookup", json={"restaurant_id": restaurant_a.id, "phone_number": phone})

    res = client.get(
        f"/api/v1/loyalty/by-restaurant/{restaurant_b.id}/member",
        params={"phone_number": phone},
        headers=headers_a,
    )
    assert res.status_code == 403


def test_birthday_flag_reflects_todays_date(client):
    import datetime

    restaurant, _table, _item, _headers = _setup_restaurant(client)
    today = datetime.date.today()
    body = client.post(
        "/api/v1/loyalty/lookup",
        json={
            "restaurant_id": restaurant.id,
            "phone_number": "20333444",
            "birth_date": today.isoformat(),
        },
    ).json()
    assert body["is_birthday_today"] is True


def test_no_birthday_flag_when_date_not_today(client):
    restaurant, _table, _item, _headers = _setup_restaurant(client)
    body = client.post(
        "/api/v1/loyalty/lookup",
        json={"restaurant_id": restaurant.id, "phone_number": "20333444", "birth_date": "2000-01-01"},
    ).json()
    assert body["is_birthday_today"] is False
