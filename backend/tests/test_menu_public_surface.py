"""
S-1 (audit de pré-lancement, 2026-08-18) : `GET /menu-items/by-restaurant/{id}`
et `/suggestions` étaient publics et acceptaient un identifiant incrémental —
la carte et les prix de n'importe quel établissement se lisaient sans jeton,
juste en devinant un entier.

Ces deux routes restent nécessaires au dashboard manager (authentifié), donc
fermées ici plutôt que supprimées. Le parcours client, lui, passe désormais
par `/by-table/{qr_token}` — même principe que les commandes depuis la
Phase 12.2 : « public » ne veut pas dire « non lié ».
"""
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup(client):
    restaurant = create_restaurant(name="Chez Slah", slug="menu-public-surface")
    manager_headers = auth_headers(create_staff(restaurant.id, StaffRole.MANAGER))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "category": "Plats", "price": 22},
        headers=manager_headers,
    ).json()
    return restaurant, table, item, manager_headers


def test_menu_by_restaurant_requires_authentication(client):
    restaurant, _table, _item, _headers = _setup(client)

    res = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}")
    assert res.status_code == 401


def test_menu_by_restaurant_forbidden_for_another_restaurant(client):
    restaurant, _table, _item, _headers = _setup(client)
    other_manager = auth_headers(create_staff(create_restaurant(name="Voisin", slug="menu-public-voisin").id))

    res = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=other_manager)
    assert res.status_code == 403


def test_suggestions_by_restaurant_requires_authentication(client):
    restaurant, _table, _item, _headers = _setup(client)

    res = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions")
    assert res.status_code == 401


def test_suggestions_by_restaurant_forbidden_for_another_restaurant(client):
    restaurant, _table, _item, _headers = _setup(client)
    other_manager = auth_headers(create_staff(create_restaurant(name="Voisin2", slug="menu-public-voisin-2").id))

    res = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions", headers=other_manager)
    assert res.status_code == 403


def test_menu_by_table_is_public_and_scoped_to_the_qr_token(client):
    """Le parcours client (scan QR) : public, mais lié à la table — pas un
    identifiant à deviner."""
    _restaurant, table, item, _headers = _setup(client)

    res = client.get(f"/api/v1/menu-items/by-table/{table['qr_token']}")
    assert res.status_code == 200
    assert [i["id"] for i in res.json()] == [item["id"]]


def test_menu_by_table_rejects_an_unknown_token(client):
    res = client.get("/api/v1/menu-items/by-table/un-token-invente")
    assert res.status_code == 404


def test_suggestions_by_table_is_public_and_scoped_to_the_qr_token(client):
    _restaurant, table, item, headers = _setup(client)
    other_item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": _restaurant.id, "name": "Thé", "category": "Boissons", "price": 3},
        headers=headers,
    ).json()
    client.put(
        f"/api/v1/menu-items/{item['id']}/suggestions",
        json={"suggested_item_ids": [other_item["id"]]},
        headers=headers,
    )

    res = client.get(f"/api/v1/menu-items/by-table/{table['qr_token']}/suggestions")
    assert res.status_code == 200
    assert res.json() == {str(item["id"]): [other_item["id"]]}
