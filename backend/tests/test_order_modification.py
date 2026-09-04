"""
Modification d'une commande après envoi — deux fenêtres :

- Fenêtre 1 (ce fichier, `PUT /orders/{id}/items`) : le client modifie
  lui-même sa commande tant qu'elle est `PENDING_CONFIRMATION`.
- Fenêtre 2 (`test_order_modification_requests.py`) : une fois confirmée, le
  client passe par une demande que le serveur valide ligne par ligne.
"""
from app.modules.orders.models import Order
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup_restaurant_with_two_items(client):
    # Pas de slug fixe : cette fixture est appelée plusieurs fois dans les
    # tests d'isolation multi-restaurant, un slug en dur collisionnerait.
    restaurant = create_restaurant(name="Café Test")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 5"}, headers=headers
    ).json()
    couscous = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous royal", "price": 24.0},
        headers=headers,
    ).json()
    the = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Thé à la menthe", "price": 3.0},
        headers=headers,
    ).json()
    return restaurant, table, couscous, the, headers


def _create_order(client, table, couscous, quantity=2):
    return client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": couscous["id"], "quantity": quantity}]},
    ).json()


def test_client_can_edit_order_while_pending_confirmation(client):
    restaurant, table, couscous, the, _headers = _setup_restaurant_with_two_items(client)
    order = _create_order(client, table, couscous, quantity=2)
    assert order["items_updated_at"] is None

    res = client.put(
        f"/api/v1/orders/{order['id']}/items",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 1}, {"menu_item_id": the["id"], "quantity": 3}]},
        headers=order_headers(order),
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["items_updated_at"] is not None
    quantities = {i["menu_item_name"]: i["quantity"] for i in updated["items"]}
    assert quantities == {"Couscous royal": 1, "Thé à la menthe": 3}
    assert updated["total_amount"] == 1 * 24.0 + 3 * 3.0


def test_edit_replaces_items_entirely_not_merges(client):
    """
    Envoyer le panier voulu dans son ensemble : un article retiré du payload
    doit disparaître de la commande, pas juste rester à son ancienne quantité.
    """
    restaurant, table, couscous, the, _headers = _setup_restaurant_with_two_items(client)
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [
                {"menu_item_id": couscous["id"], "quantity": 2},
                {"menu_item_id": the["id"], "quantity": 3},
            ],
        },
    ).json()

    res = client.put(
        f"/api/v1/orders/{order['id']}/items",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}]},
        headers=order_headers(order),
    )
    assert res.status_code == 200
    updated = res.json()
    assert [i["menu_item_name"] for i in updated["items"]] == ["Couscous royal"]


def test_client_cannot_edit_order_once_confirmed(client):
    """
    Risque business direct : passé la confirmation, une édition directe ne
    doit jamais écraser silencieusement une commande déjà vérifiée avec la
    table (voire déjà en cuisine).
    """
    restaurant, table, couscous, the, headers = _setup_restaurant_with_two_items(client)
    order = _create_order(client, table, couscous)
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers)

    res = client.put(
        f"/api/v1/orders/{order['id']}/items",
        json={"items": [{"menu_item_id": the["id"], "quantity": 1}]},
        headers=order_headers(order),
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ORDER_NOT_MODIFIABLE"


def test_edit_rejects_empty_items(client):
    restaurant, table, couscous, _the, _headers = _setup_restaurant_with_two_items(client)
    order = _create_order(client, table, couscous)

    res = client.put(
        f"/api/v1/orders/{order['id']}/items", json={"items": []}, headers=order_headers(order)
    )
    assert res.status_code == 422


def test_edit_requires_the_matching_order_token(client):
    """
    Jamais 401/403 sur les routes client : un token absent ou faux répond 404,
    comme le reste des routes de suivi (constat 1 de la revue du 2026-08-13)."""
    restaurant, table, couscous, the, _headers = _setup_restaurant_with_two_items(client)
    order = _create_order(client, table, couscous)

    no_token = client.put(
        f"/api/v1/orders/{order['id']}/items", json={"items": [{"menu_item_id": the["id"], "quantity": 1}]}
    )
    assert no_token.status_code == 404

    wrong_token = client.put(
        f"/api/v1/orders/{order['id']}/items",
        json={"items": [{"menu_item_id": the["id"], "quantity": 1}]},
        headers={"X-Order-Token": "not-the-real-token"},
    )
    assert wrong_token.status_code == 404


def test_edit_rejects_item_from_another_restaurant(client):
    restaurant, table, couscous, _the, _headers = _setup_restaurant_with_two_items(client)
    order = _create_order(client, table, couscous)

    _other_restaurant, _other_table, other_item, _other_the, _other_headers = (
        _setup_restaurant_with_two_items(client)
    )

    res = client.put(
        f"/api/v1/orders/{order['id']}/items",
        json={"items": [{"menu_item_id": other_item["id"], "quantity": 1}]},
        headers=order_headers(order),
    )
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "ITEM_NOT_FOUND"


def test_edit_broadcasts_to_staff_pool(client, db_session):
    """Le pool serveur doit voir que la commande a changé avant de confirmer
    dessus — vérifié ici via l'état persisté plutôt que le WebSocket lui-même
    (déjà couvert par les tests waiter_calls pour le mécanisme de diffusion)."""
    restaurant, table, couscous, the, _headers = _setup_restaurant_with_two_items(client)
    order = _create_order(client, table, couscous)

    client.put(
        f"/api/v1/orders/{order['id']}/items",
        json={"items": [{"menu_item_id": the["id"], "quantity": 2}]},
        headers=order_headers(order),
    )

    stored = db_session.get(Order, order["id"])
    assert stored.items_updated_at is not None
