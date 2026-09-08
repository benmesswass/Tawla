"""
Détail des commandes terminées par la cuisine (onglet "Terminées" de l'écran
cuisine) — jusqu'ici l'onglet n'affichait qu'un compteur, sans le détail des
plats, ce qui empêchait de revérifier une commande après coup (réclamation
client, erreur signalée après le service).
"""
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup(client):
    restaurant = create_restaurant(name="Café Test", slug="cafe-cuisine-done")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 12.0},
        headers=headers,
    ).json()
    return restaurant, table, item


def _order_marked_ready(client, table, item, waiter, kitchen, quantity=2, notes=None):
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": quantity, "notes": notes}],
        },
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(waiter))
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(waiter))
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=auth_headers(kitchen))
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=auth_headers(kitchen))
    return order


def test_kitchen_done_today_shows_order_detail(client):
    """
    C'est l'objet même de la fonctionnalité : une fois une commande marquée
    prête, la cuisine doit pouvoir en revoir le détail (plats, quantités,
    notes) — pas seulement un compteur.
    """
    restaurant, table, item = _setup(client)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = _order_marked_ready(client, table, item, waiter, kitchen, quantity=3, notes="sans oignons")

    done = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/kitchen-done-today", headers=auth_headers(kitchen)
    )

    assert done.status_code == 200
    body = done.json()
    assert len(body) == 1
    assert body[0]["id"] == order["id"]
    assert body[0]["table_label"] == "Table 1"
    assert body[0]["status"] == "ready"
    assert body[0]["items"][0]["menu_item_name"] == "Couscous"
    assert body[0]["items"][0]["quantity"] == 3
    assert body[0]["items"][0]["notes"] == "sans oignons"


def test_kitchen_done_today_excludes_orders_still_active(client):
    """
    Une commande encore en cuisine (envoyée, pas préparée) appartient aux
    onglets "À préparer"/"En cours" — elle ne doit pas apparaître aussi dans
    "Terminées".
    """
    restaurant, table, item = _setup(client)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(waiter))
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(waiter))

    done = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/kitchen-done-today", headers=auth_headers(kitchen)
    )

    assert done.status_code == 200
    assert done.json() == []


def test_kitchen_done_today_includes_served_orders(client):
    """La cuisine n'agit plus dessus, mais doit pouvoir en revoir le détail
    même une fois la commande livrée à table."""
    restaurant, table, item = _setup(client)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = _order_marked_ready(client, table, item, waiter, kitchen)
    client.post(f"/api/v1/orders/{order['id']}/mark-served", headers=auth_headers(waiter))

    done = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/kitchen-done-today", headers=auth_headers(kitchen)
    )

    assert done.status_code == 200
    assert len(done.json()) == 1
    assert done.json()[0]["status"] == "served"


def test_kitchen_done_today_excludes_cancelled_orders(client):
    """
    Annulée n'est pas "terminée" au sens de cet onglet : la cuisine n'a rien
    préparé, ça ne doit pas s'afficher comme si c'était le cas.
    """
    restaurant, table, item = _setup(client)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/cancel", headers=auth_headers(waiter))

    done = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/kitchen-done-today", headers=auth_headers(kitchen)
    )

    assert done.status_code == 200
    assert done.json() == []


def test_kitchen_done_today_forbidden_for_waiter(client):
    """Même restriction que les autres actions cuisine (start-preparation,
    mark-ready) : un serveur n'a pas accès à l'écran cuisine."""
    restaurant, _table, _item = _setup(client)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    res = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/kitchen-done-today", headers=auth_headers(waiter)
    )

    assert res.status_code == 403


def test_kitchen_done_today_forbidden_for_other_restaurant(client):
    restaurant_a, _table, _item = _setup(client)
    restaurant_b = create_restaurant(name="Autre resto", slug="cafe-cuisine-done-b")
    kitchen_a = create_staff(restaurant_a.id, StaffRole.KITCHEN)

    res = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant_b.id}/kitchen-done-today", headers=auth_headers(kitchen_a)
    )

    assert res.status_code == 403
