from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_items(client):
    restaurant = create_restaurant(name="Dar Chaabane", slug="dar-chaabane-shared")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    salade = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Salade méchouia", "category": "Entrées", "price": 6.0},
        headers=headers,
    ).json()
    couscous = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "category": "Plats", "price": 15.0},
        headers=headers,
    ).json()
    return restaurant, table, salade, couscous, headers


def test_order_item_is_shared_flag_is_persisted(client):
    restaurant, table, salade, couscous, _headers = _setup_restaurant_with_items(client)
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [
                {"menu_item_id": salade["id"], "quantity": 1, "is_shared": True},
                {"menu_item_id": couscous["id"], "quantity": 2, "is_shared": False},
            ],
        },
    ).json()

    by_item_id = {i["menu_item_id"]: i for i in order["items"]}
    assert by_item_id[salade["id"]]["is_shared"] is True
    assert by_item_id[couscous["id"]]["is_shared"] is False


def test_order_item_is_shared_defaults_to_false(client):
    """Un client qui ne coche rien ne doit jamais se retrouver avec un plat marqué à tort comme partagé."""
    restaurant, table, salade, _couscous, _headers = _setup_restaurant_with_items(client)
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": salade["id"], "quantity": 1}],
        },
    ).json()
    assert order["items"][0]["is_shared"] is False
