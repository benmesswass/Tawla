from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    restaurant = create_restaurant(name="Dar Chaabane", slug="dar-chaabane-labels")
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def test_menu_item_defaults_no_spice_and_halal(client):
    """Un article créé sans préciser ces champs doit rester cohérent avec le contexte tunisien."""
    restaurant, headers = _setup_restaurant(client)
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 15.0},
        headers=headers,
    ).json()
    assert item["spice_level"] == 0
    assert item["allergens"] is None
    assert item["is_halal"] is True


def test_menu_item_can_set_spice_allergens_and_halal(client):
    restaurant, headers = _setup_restaurant(client)
    item = client.post(
        "/api/v1/menu-items",
        json={
            "restaurant_id": restaurant.id,
            "name": "Merguez piquante",
            "price": 12.0,
            "spice_level": 3,
            "allergens": "Gluten, Fruits à coque",
            "is_halal": True,
        },
        headers=headers,
    ).json()
    assert item["spice_level"] == 3
    assert item["allergens"] == "Gluten, Fruits à coque"


def test_menu_item_rejects_out_of_range_spice_level(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Trop épicé", "price": 12.0, "spice_level": 5},
        headers=headers,
    )
    assert res.status_code == 422


def test_menu_item_update_can_change_labels(client):
    restaurant, headers = _setup_restaurant(client)
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Salade", "price": 6.0},
        headers=headers,
    ).json()

    updated = client.patch(
        f"/api/v1/menu-items/{item['id']}",
        json={"spice_level": 2, "allergens": "Fruits à coque", "is_halal": False},
        headers=headers,
    ).json()
    assert updated["spice_level"] == 2
    assert updated["allergens"] == "Fruits à coque"
    assert updated["is_halal"] is False
