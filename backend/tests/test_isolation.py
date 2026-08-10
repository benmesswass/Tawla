from tests.conftest import auth_headers, create_staff


def test_cannot_order_item_from_another_restaurant(client):
    """
    Risque critique en SaaS multi-tenant : si l'isolation par restaurant_id
    a une faille, une table du resto A peut commander le menu du resto B.
    """
    resto_a = client.post("/api/v1/restaurants", json={"name": "Resto A", "slug": "resto-a"}).json()
    resto_b = client.post("/api/v1/restaurants", json={"name": "Resto B", "slug": "resto-b"}).json()
    headers_a = auth_headers(create_staff(resto_a["id"]))
    headers_b = auth_headers(create_staff(resto_b["id"]))

    table_a = client.post(
        "/api/v1/tables", json={"restaurant_id": resto_a["id"], "label": "Table 1"}, headers=headers_a
    ).json()
    item_b = client.post(
        "/api/v1/menu-items", json={"restaurant_id": resto_b["id"], "name": "Plat B", "price": 10}, headers=headers_b
    ).json()

    res = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": resto_a["id"],
            "table_id": table_a["id"],
            "items": [{"menu_item_id": item_b["id"], "quantity": 1}],
        },
    )
    assert res.status_code == 404


def test_cannot_use_table_from_another_restaurant(client):
    resto_a = client.post("/api/v1/restaurants", json={"name": "Resto A2", "slug": "resto-a2"}).json()
    resto_b = client.post("/api/v1/restaurants", json={"name": "Resto B2", "slug": "resto-b2"}).json()
    headers_a = auth_headers(create_staff(resto_a["id"]))
    headers_b = auth_headers(create_staff(resto_b["id"]))

    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": resto_b["id"], "label": "Table 1"}, headers=headers_b
    ).json()
    item_a = client.post(
        "/api/v1/menu-items", json={"restaurant_id": resto_a["id"], "name": "Plat A", "price": 10}, headers=headers_a
    ).json()

    res = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": resto_a["id"],
            "table_id": table_b["id"],
            "items": [{"menu_item_id": item_a["id"], "quantity": 1}],
        },
    )
    assert res.status_code == 404


def test_table_qr_tokens_are_unique_and_opaque(client):
    """
    Un client ne doit jamais pouvoir deviner le QR d'une autre table en
    modifiant l'URL (ex: incrémenter un ID).
    """
    restaurant = client.post("/api/v1/restaurants", json={"name": "Resto C", "slug": "resto-c"}).json()
    headers = auth_headers(create_staff(restaurant["id"]))
    table_1 = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 1"}, headers=headers
    ).json()
    table_2 = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 2"}, headers=headers
    ).json()

    assert table_1["qr_token"] != table_2["qr_token"]
    assert len(table_1["qr_token"]) >= 16  # pas un simple ID court devinable

    res = client.get("/api/v1/tables/by-token/un-token-invente-qui-nexiste-pas")
    assert res.status_code == 404


def test_staff_cannot_list_active_orders_of_another_restaurant(client):
    """Un manager du resto A ne doit pas pouvoir consulter le pool de commandes du resto B."""
    resto_a = client.post("/api/v1/restaurants", json={"name": "Resto D", "slug": "resto-d"}).json()
    resto_b = client.post("/api/v1/restaurants", json={"name": "Resto E", "slug": "resto-e"}).json()
    headers_a = auth_headers(create_staff(resto_a["id"]))

    res = client.get(f"/api/v1/orders/by-restaurant/{resto_b['id']}/active", headers=headers_a)
    assert res.status_code == 403
