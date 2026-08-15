import uuid

from app.modules.loyalty.models import LOYALTY_REWARD_THRESHOLD, LoyaltyMember
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


def _place_order(client, table, item, phone, birth_date=None):
    """La commande est le seul chemin qui crée une fiche fidélité : le client y
    donne son propre numéro, sur sa propre table (Phase 19.1)."""
    payload = {
        "qr_token": table["qr_token"],
        "items": [{"menu_item_id": item["id"], "quantity": 1}],
        "loyalty_phone": phone,
    }
    if birth_date:
        payload["loyalty_birth_date"] = birth_date
    return client.post("/api/v1/orders", json=payload).json()


def _order_and_pay_by_card(client, restaurant, table, item, phone):
    order = _place_order(client, table, item, phone)
    return client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    ).json()


def _lookup(client, table, phone):
    return client.post(
        "/api/v1/loyalty/lookup", json={"qr_token": table["qr_token"], "phone_number": phone}
    )


def test_lookup_fidelite_ne_cree_jamais_de_fiche(client, db_session):
    """
    Défaut T1 : cette route publique créait une fiche pour tout numéro qu'on
    lui soumettait. Enregistrer le numéro d'un tiers qui n'a rien commandé n'a
    aucune finalité au sens de la loi 2004-63 — et la promesse affichée au
    client dit que son numéro ne sert qu'à la fidélité de cet établissement.
    """
    _restaurant, table, _item, _headers = _setup_restaurant(client)

    res = _lookup(client, table, "20123456")

    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "LOYALTY_MEMBER_NOT_FOUND"
    assert db_session.query(LoyaltyMember).count() == 0


def test_lookup_fidelite_refuse_sans_qr_token(client):
    """
    Sans le token de la table, la réponse doit être la même pour un numéro
    client et pour un numéro inconnu : toute différence transforme la route en
    test d'appartenance, exactement ce que la Phase 19.1 ferme.
    """
    _restaurant, table, item, _headers = _setup_restaurant(client)
    connu = "20123456"
    _place_order(client, table, item, connu)

    sans_token_connu = client.post("/api/v1/loyalty/lookup", json={"phone_number": connu})
    sans_token_inconnu = client.post("/api/v1/loyalty/lookup", json={"phone_number": "20999000"})
    assert sans_token_connu.status_code == sans_token_inconnu.status_code == 422

    faux_token_connu = client.post(
        "/api/v1/loyalty/lookup", json={"qr_token": "token-invente", "phone_number": connu}
    )
    faux_token_inconnu = client.post(
        "/api/v1/loyalty/lookup", json={"qr_token": "token-invente", "phone_number": "20999000"}
    )
    assert faux_token_connu.status_code == faux_token_inconnu.status_code == 404
    assert faux_token_connu.json() == faux_token_inconnu.json()


def test_lookup_retrouve_la_fiche_creee_par_la_commande(client):
    _restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20123456"
    _place_order(client, table, item, phone)

    res = _lookup(client, table, phone)

    assert res.status_code == 200
    body = res.json()
    assert body["order_count"] == 0
    assert body["reward_available"] is False
    assert body["orders_until_reward"] == LOYALTY_REWARD_THRESHOLD


def test_order_count_only_increments_on_confirmed_payment(client):
    """Une commande jamais payée ne doit jamais faire gagner de point."""
    _restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20123456"

    _place_order(client, table, item, phone)

    assert _lookup(client, table, phone).json()["order_count"] == 0


def test_order_count_increments_on_card_payment(client):
    restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20123456"

    order = _order_and_pay_by_card(client, restaurant, table, item, phone)
    assert order["payment_status"] == "paid"

    assert _lookup(client, table, phone).json()["order_count"] == 1


def test_order_count_increments_on_confirmed_cash_payment(client):
    _restaurant, table, item, manager_headers = _setup_restaurant(client)
    phone = "20654321"

    order = _place_order(client, table, item, phone)
    client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))
    # Une demande cash seule (pas encore encaissée) ne doit rien faire gagner.
    assert _lookup(client, table, phone).json()["order_count"] == 0

    client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    assert _lookup(client, table, phone).json()["order_count"] == 1


def test_reward_becomes_available_at_threshold(client):
    restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20111222"

    for _ in range(LOYALTY_REWARD_THRESHOLD):
        order = _order_and_pay_by_card(client, restaurant, table, item, phone)

    status = _lookup(client, table, phone).json()
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
    _restaurant, table, item, manager_headers = _setup_restaurant(client)
    phone = "20999888"
    _place_order(client, table, item, phone)
    member = _lookup(client, table, phone).json()

    res = client.post(f"/api/v1/loyalty/{member['id']}/redeem", headers=manager_headers)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "NO_REWARD_AVAILABLE"


def test_staff_member_lookup_requires_role(client):
    restaurant, table, item, _manager_headers = _setup_restaurant(client)
    _place_order(client, table, item, "20999888")

    kitchen_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.KITCHEN))
    res = client.get(
        f"/api/v1/loyalty/by-restaurant/{restaurant.id}/member",
        params={"phone_number": "20999888"},
        headers=kitchen_headers,
    )
    assert res.status_code == 403


def test_loyalty_is_isolated_per_restaurant(client):
    _restaurant_a, table_a, item_a, headers_a = _setup_restaurant(client)
    restaurant_b, _table_b, _item_b, _headers_b = _setup_restaurant(client)
    phone = "20111222"

    _place_order(client, table_a, item_a, phone)

    res = client.get(
        f"/api/v1/loyalty/by-restaurant/{restaurant_b.id}/member",
        params={"phone_number": phone},
        headers=headers_a,
    )
    assert res.status_code == 403


def test_birthday_flag_reflects_todays_date(client):
    import datetime

    _restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20333444"
    # La date de naissance se donne avec sa propre commande depuis la Phase
    # 19.1 : la route de consultation ne peut plus rien écrire.
    _place_order(client, table, item, phone, birth_date=datetime.date.today().isoformat())

    assert _lookup(client, table, phone).json()["is_birthday_today"] is True


def test_no_birthday_flag_when_date_not_today(client):
    _restaurant, table, item, _headers = _setup_restaurant(client)
    phone = "20333444"
    _place_order(client, table, item, phone, birth_date="2000-01-01")

    assert _lookup(client, table, phone).json()["is_birthday_today"] is False
