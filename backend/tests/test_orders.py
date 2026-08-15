from app.modules.orders.models import Order
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_item(client, available=True, price=3.5):
    restaurant = create_restaurant(name="Café Test", slug="cafe-test")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Café", "price": price},
        headers=headers,
    ).json()
    if not available:
        client.patch(f"/api/v1/menu-items/{item['id']}/availability", json={"is_available": False}, headers=headers)
    return restaurant, table, item, headers


def test_order_full_happy_path(client):
    """Le flux décrit par Wass : client commande -> serveur confirme -> cuisine."""
    restaurant, table, item, headers = _setup_restaurant_with_item(client)

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 2}],
        },
    ).json()
    assert order["status"] == "pending_confirmation"

    confirmed = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers).json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"] is not None

    sent = client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=headers).json()
    assert sent["status"] == "sent_to_kitchen"
    assert sent["sent_to_kitchen_at"] is not None


def test_cannot_send_to_kitchen_without_waiter_confirmation(client):
    """
    Risque business direct : si on peut sauter l'étape de confirmation,
    une commande non vérifiée par le serveur part en cuisine.
    """
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    ).json()

    res = client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=headers)
    assert res.status_code == 409


def test_cannot_order_unavailable_item(client):
    restaurant, table, item, _headers = _setup_restaurant_with_item(client, available=False)
    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    )
    assert res.status_code == 409


def test_order_price_is_frozen_at_order_time(client):
    """
    Si le resto change ses prix, ça ne doit JAMAIS modifier une commande
    déjà passée (litige client sinon).
    """
    restaurant, table, item, headers = _setup_restaurant_with_item(client, price=3.5)
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    ).json()

    # Le prix du menu change après coup...
    client.patch(f"/api/v1/menu-items/{item['id']}/availability", json={"is_available": True}, headers=headers)

    # ... la ligne de commande déjà créée reste figée
    assert float(order["items"][0]["unit_price"]) == 3.5


def test_empty_order_is_rejected(client):
    restaurant, table, _item, _headers = _setup_restaurant_with_item(client)
    res = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": []},
    )
    assert res.status_code == 422


# --- T2 : idempotence de la création de commande (Phase 19.2) -----------------


def _panier(table, item, client_order_id=None, quantity=2):
    payload = {
        "qr_token": table["qr_token"],
        "items": [{"menu_item_id": item["id"], "quantity": quantity}],
    }
    if client_order_id:
        payload["client_order_id"] = client_order_id
    return payload


def test_deux_envois_du_meme_panier_ne_font_quune_commande(client, db_session):
    """
    Défaut T2 : une réponse perdue en plein service — réseau coupé au mauvais
    moment, ou file hors ligne rejouée — produisait deux commandes, donc deux
    préparations. Le restaurant sert deux fois ce que le client paie une fois.
    """
    _restaurant, table, item, _headers = _setup_restaurant_with_item(client)
    payload = _panier(table, item, client_order_id="panier-abc-123")

    first = client.post("/api/v1/orders", json=payload)
    second = client.post("/api/v1/orders", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    # Le téléphone doit retomber sur SA commande : avec un autre token, le
    # client ne pourrait plus ni la suivre ni la payer.
    assert first.json()["public_token"] == second.json()["public_token"]
    assert db_session.query(Order).count() == 1


def test_deux_paniers_differents_restent_deux_commandes(client, db_session):
    """Le filet ne doit pas avaler une vraie deuxième tournée."""
    _restaurant, table, item, _headers = _setup_restaurant_with_item(client)

    first = client.post("/api/v1/orders", json=_panier(table, item, "panier-1"))
    second = client.post("/api/v1/orders", json=_panier(table, item, "panier-2", quantity=1))

    assert first.json()["id"] != second.json()["id"]
    assert db_session.query(Order).count() == 2


def test_une_commande_sans_identifiant_de_panier_reste_creee(client, db_session):
    """Le champ est facultatif : un client sur une version antérieure de la
    page continue de commander, et deux envois restent deux commandes."""
    _restaurant, table, item, _headers = _setup_restaurant_with_item(client)

    client.post("/api/v1/orders", json=_panier(table, item))
    client.post("/api/v1/orders", json=_panier(table, item))

    assert db_session.query(Order).count() == 2


def test_un_rejeu_ne_reveille_pas_une_seconde_fois_lecran_serveur(client):
    """
    Sans ça, la commande réapparaît sur l'écran serveur alors qu'elle est déjà
    prise en charge, et le serveur la traite une deuxième fois.

    L'absence de second message se prouve en provoquant ensuite un événement
    distinct : s'il arrive en premier, c'est qu'aucun doublon ne l'a précédé.
    """
    restaurant, table, item, _headers = _setup_restaurant_with_item(client)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    token = auth_headers(waiter)["Authorization"].split()[1]
    rejoue = _panier(table, item, "panier-1")

    with client.websocket_connect(f"/ws/staff/{restaurant.id}?token={token}") as ws:
        premier = client.post("/api/v1/orders", json=rejoue).json()
        assert ws.receive_json()["order_id"] == premier["id"]

        client.post("/api/v1/orders", json=rejoue)
        suivant = client.post("/api/v1/orders", json=_panier(table, item, "panier-2", quantity=1)).json()

        assert ws.receive_json()["order_id"] == suivant["id"]
