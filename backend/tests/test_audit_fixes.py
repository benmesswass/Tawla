"""
Régressions ajoutées suite à l'audit QA/PO/Design du 2026-08-10. Chaque test
reproduit un bug constaté manuellement avant correction.
"""
from app.modules.staff.models import Staff
from tests.conftest import _TestingSessionLocal


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


def test_active_orders_survive_a_late_or_refreshed_screen(client):
    """
    Bug critique trouvé à l'audit : un écran serveur/cuisine ouvert (ou
    rafraîchi) APRÈS qu'une commande soit passée ne la voyait jamais, car
    tout reposait uniquement sur le push WebSocket au moment de la création.
    """
    restaurant, table, item = _setup_restaurant_with_item(client)
    order = client.post(
        "/api/v1/orders",
        json={"restaurant_id": restaurant["id"], "table_id": table["id"], "items": [{"menu_item_id": item["id"]}]},
    ).json()

    res = client.get(f"/api/v1/orders/by-restaurant/{restaurant['id']}/active")
    assert res.status_code == 200
    assert order["id"] in [o["id"] for o in res.json()]


def test_active_orders_excludes_served_and_cancelled(client):
    restaurant, table, item = _setup_restaurant_with_item(client)
    order = client.post(
        "/api/v1/orders",
        json={"restaurant_id": restaurant["id"], "table_id": table["id"], "items": [{"menu_item_id": item["id"]}]},
    ).json()
    order_id = order["id"]
    client.post(f"/api/v1/orders/{order_id}/confirm")
    client.post(f"/api/v1/orders/{order_id}/send-to-kitchen")
    client.post(f"/api/v1/orders/{order_id}/start-preparation")
    client.post(f"/api/v1/orders/{order_id}/mark-ready")
    client.post(f"/api/v1/orders/{order_id}/mark-served")

    res = client.get(f"/api/v1/orders/by-restaurant/{restaurant['id']}/active")
    assert order_id not in [o["id"] for o in res.json()]


def test_error_responses_carry_a_machine_readable_code(client):
    """
    Bug majeur trouvé à l'audit : les messages d'erreur bruts ("invalid
    table code", "'X' is no longer available") étaient affichés tels quels,
    en anglais, à l'utilisateur final. Le frontend a besoin d'un code stable
    pour les traduire, pas d'un texte libre.
    """
    res = client.get("/api/v1/tables/by-token/un-token-invente")
    assert res.json()["detail"]["code"] == "INVALID_TABLE_CODE"

    restaurant = client.post(
        "/api/v1/restaurants", json={"name": "Café Test 2", "slug": "cafe-test-2"}
    ).json()
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant["id"], "label": "Table 1"}
    ).json()
    unavailable_item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant["id"], "name": "Plat épuisé", "price": 9},
    ).json()
    client.patch(f"/api/v1/menu-items/{unavailable_item['id']}/availability", json={"is_available": False})

    res = client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": restaurant["id"],
            "table_id": table["id"],
            "items": [{"menu_item_id": unavailable_item["id"]}],
        },
    )
    assert res.json()["detail"]["code"] == "ITEM_UNAVAILABLE"
    assert res.json()["detail"]["item_name"] == "Plat épuisé"


def test_assign_staff_rejects_unknown_staff_id(client):
    """
    Bug majeur trouvé à l'audit : assign-staff acceptait n'importe quel
    staff_id, y compris un ID qui n'existe pas (200 OK).
    """
    _, table, _ = _setup_restaurant_with_item(client)
    res = client.post(f"/api/v1/tables/{table['id']}/assign-staff", json={"staff_id": 999999})
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "STAFF_NOT_FOUND"


def test_assign_staff_rejects_staff_from_another_restaurant(client):
    """
    Même bug, variante isolation multi-tenant : un staff du resto B ne doit
    pas pouvoir être assigné à une table du resto A.
    """
    resto_a, table_a, _ = _setup_restaurant_with_item(client)
    resto_b = client.post("/api/v1/restaurants", json={"name": "Resto B", "slug": "resto-b-audit"}).json()

    db = _TestingSessionLocal()
    staff_b = Staff(restaurant_id=resto_b["id"], name="Karim")
    db.add(staff_b)
    db.commit()
    staff_b_id = staff_b.id
    db.close()

    res = client.post(f"/api/v1/tables/{table_a['id']}/assign-staff", json={"staff_id": staff_b_id})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "STAFF_WRONG_RESTAURANT"


def test_dashboard_can_update_and_delete_menu_items(client):
    """
    Bug produit trouvé à l'audit : gérer le menu nécessitait de passer par
    Swagger. Le dashboard resto s'appuie sur ces deux endpoints.
    """
    restaurant, _, item = _setup_restaurant_with_item(client, price=4)

    res = client.patch(f"/api/v1/menu-items/{item['id']}", json={"price": 5.5, "name": "Café renommé"})
    assert res.status_code == 200
    assert res.json()["price"] == 5.5
    assert res.json()["name"] == "Café renommé"

    res = client.delete(f"/api/v1/menu-items/{item['id']}")
    assert res.status_code == 204

    res = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant['id']}")
    assert item["id"] not in [i["id"] for i in res.json()]


def test_menu_sorted_in_meal_order_not_alphabetically(client):
    """
    Bug mineur (produit) trouvé à l'audit : le tri alphabétique de catégorie
    montrait les boissons/desserts avant les plats.
    """
    restaurant = client.post("/api/v1/restaurants", json={"name": "Resto Menu", "slug": "resto-menu-audit"}).json()
    for category, name in [
        ("Boissons", "Thé"),
        ("Desserts", "Baklawa"),
        ("Entrées", "Salade"),
        ("Plats", "Couscous"),
    ]:
        client.post(
            "/api/v1/menu-items",
            json={"restaurant_id": restaurant["id"], "name": name, "category": category, "price": 5},
        )

    res = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant['id']}")
    categories = [item["category"] for item in res.json()]
    assert categories == ["Entrées", "Plats", "Desserts", "Boissons"]
