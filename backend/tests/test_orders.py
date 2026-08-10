def _setup_restaurant_with_item(client, available=True, price=3.5):
    restaurant = client.post(
        "/api/v1/restaurants", json={"name": "Café Test", "slug": "cafe-test"}
    ).json()
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 1"}
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant["id"], "name": "Café", "price": price},
    ).json()
    if not available:
        client.patch(f"/api/v1/menu-items/{item['id']}/availability", json={"is_available": False})
    return restaurant, table, item


def test_order_full_happy_path(client):
    """Le flux décrit par Wass : client commande -> serveur confirme -> cuisine."""
    restaurant, table, item = _setup_restaurant_with_item(client)

    order = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 2}],
        },
    ).json()
    assert order["status"] == "pending_confirmation"

    confirmed = client.post(f"/api/v1/orders/{order['id']}/confirm").json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"] is not None

    sent = client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen").json()
    assert sent["status"] == "sent_to_kitchen"
    assert sent["sent_to_kitchen_at"] is not None


def test_cannot_send_to_kitchen_without_waiter_confirmation(client):
    """
    Risque business direct : si on peut sauter l'étape de confirmation,
    une commande non vérifiée par le serveur part en cuisine.
    """
    restaurant, table, item = _setup_restaurant_with_item(client)
    order = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    ).json()

    res = client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen")
    assert res.status_code == 409


def test_cannot_order_unavailable_item(client):
    restaurant, table, item = _setup_restaurant_with_item(client, available=False)
    res = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    )
    assert res.status_code == 409


def test_order_price_is_frozen_at_order_time(client):
    """
    Si le resto change ses prix, ça ne doit JAMAIS modifier une commande
    déjà passée (litige client sinon).
    """
    restaurant, table, item = _setup_restaurant_with_item(client, price=3.5)
    order = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    ).json()

    # Le prix du menu change après coup...
    client.patch(f"/api/v1/menu-items/{item['id']}/availability", json={"is_available": True})

    # ... la ligne de commande déjà créée reste figée
    assert float(order["items"][0]["unit_price"]) == 3.5


def test_empty_order_is_rejected(client):
    restaurant, table, _ = _setup_restaurant_with_item(client)
    res = client.post(
        "/api/v1/orders",
        json={"restaurant_id": restaurant["id"], "table_id": table["id"], "items": []},
    )
    assert res.status_code == 422
