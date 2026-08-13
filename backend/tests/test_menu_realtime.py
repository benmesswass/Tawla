from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_item(client):
    restaurant = create_restaurant(name="Dar Chaabane", slug="dar-chaabane-menu-realtime")
    headers = auth_headers(create_staff(restaurant.id))
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 15.0},
        headers=headers,
    ).json()
    return restaurant, item, headers


def test_availability_change_broadcasts_to_menu_channel(client):
    """
    Un client qui a la page menu ouverte doit voir une rupture de stock
    disparaître instantanément, sans attendre de tenter de commander.
    """
    restaurant, item, headers = _setup_restaurant_with_item(client)

    with client.websocket_connect(f"/ws/menu/{restaurant.id}") as ws:
        res = client.patch(
            f"/api/v1/menu-items/{item['id']}/availability",
            json={"is_available": False},
            headers=headers,
        )
        assert res.status_code == 200

        msg = ws.receive_json()
        assert msg == {
            "event": "menu_item.availability_changed",
            "menu_item_id": item["id"],
            "is_available": False,
        }
