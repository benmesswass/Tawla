"""
Occupation explicite d'une table (2026-09-09, demande de Wassim) : une table
scannée passe « occupée » et le reste tant que le serveur ou le manager ne la
libère pas explicitement via un bouton dédié — plus aucun mécanisme technique
(déconnexion, délai) ne la remet à zéro à leur place.
"""

from app.modules.orders import table_cart
from app.modules.orders.schemas import OrderItemCreate
from app.modules.staff.models import StaffRole
from app.modules.tables import party as table_party
from tests.conftest import auth_headers, create_restaurant, create_staff


def _create_table(client, restaurant, manager):
    return client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=auth_headers(manager)
    ).json()


def _occupied_at(client, restaurant, manager, table_id):
    plan = client.get(f"/api/v1/tables/plan/{restaurant.id}", headers=auth_headers(manager)).json()
    return next(t for t in plan if t["id"] == table_id)["occupied_at"]


def test_scanner_le_qr_occupe_la_table(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)

    assert _occupied_at(client, restaurant, manager, table["id"]) is None

    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")

    assert _occupied_at(client, restaurant, manager, table["id"]) is not None


def test_un_deuxieme_scan_ne_change_pas_lheure_doccupation(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)

    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")
    premiere_heure = _occupied_at(client, restaurant, manager, table["id"])

    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")
    assert _occupied_at(client, restaurant, manager, table["id"]) == premiere_heure


def test_le_serveur_peut_liberer_la_table(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    table = _create_table(client, restaurant, manager)
    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")

    response = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(waiter))

    assert response.status_code == 200, response.text
    assert response.json()["occupied_at"] is None
    assert _occupied_at(client, restaurant, manager, table["id"]) is None


def test_liberer_la_table_vide_le_panier_et_les_convives(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")
    table_cart.table_cart_store.set_line(table["id"], OrderItemCreate(menu_item_id=1))
    table_party.table_party_store.set(table["id"], 3, ["Sami", None, None])

    client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))

    assert table_cart.table_cart_store.snapshot(table["id"]) == []
    assert table_party.table_party_store.get(table["id"]) is None


def test_la_cuisine_ne_peut_pas_liberer_une_table(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    table = _create_table(client, restaurant, manager)

    response = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(kitchen))

    assert response.status_code == 403


def test_liberer_une_table_dun_autre_restaurant_est_refuse(client):
    restaurant_a = create_restaurant()
    restaurant_b = create_restaurant()
    manager_a = create_staff(restaurant_a.id, StaffRole.MANAGER)
    manager_b = create_staff(restaurant_b.id, StaffRole.MANAGER)
    table_b = _create_table(client, restaurant_b, manager_b)

    response = client.post(f"/api/v1/tables/{table_b['id']}/release", headers=auth_headers(manager_a))

    assert response.status_code == 404
