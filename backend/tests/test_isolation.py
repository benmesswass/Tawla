def test_cannot_order_item_from_another_restaurant(client):
    """
    Risque critique en SaaS multi-tenant : si l'isolation par restaurant_id
    a une faille, une table du resto A peut commander le menu du resto B.
    """
    resto_a = client.post("/api/v1/restaurants", json={"name": "Resto A", "slug": "resto-a"}).json()
    resto_b = client.post("/api/v1/restaurants", json={"name": "Resto B", "slug": "resto-b"}).json()

    table_a = client.post(
        "/api/v1/tables", json={"restaurant_id": resto_a["id"], "label": "Table 1"}
    ).json()
    item_b = client.post(
        "/api/v1/menu-items", json={"restaurant_id": resto_b["id"], "name": "Plat B", "price": 10}
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

    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": resto_b["id"], "label": "Table 1"}
    ).json()
    item_a = client.post(
        "/api/v1/menu-items", json={"restaurant_id": resto_a["id"], "name": "Plat A", "price": 10}
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
    table_1 = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 1"}
    ).json()
    table_2 = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 2"}
    ).json()

    assert table_1["qr_token"] != table_2["qr_token"]
    assert len(table_1["qr_token"]) >= 16  # pas un simple ID court devinable

    res = client.get("/api/v1/tables/by-token/un-token-invente-qui-nexiste-pas")
    assert res.status_code == 404
