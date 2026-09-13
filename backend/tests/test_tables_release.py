"""
Occupation explicite d'une table (2026-09-09, demande de Wassim) : une table
scannée passe « occupée » et le reste tant que le serveur ou le manager ne la
libère pas explicitement via un bouton dédié — plus aucun mécanisme technique
(déconnexion, délai) ne la remet à zéro à leur place.
"""

from app.modules.orders import table_cart
from app.modules.orders.schemas import OrderItemCreate
from app.modules.staff.models import StaffRole
from app.modules.tables import roster as table_roster
from app.modules.tables import service as tables_service
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers, ws_billet


def _create_table(client, restaurant, manager):
    return client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=auth_headers(manager)
    ).json()


def _create_item(client, restaurant, manager):
    return client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Café", "price": 3.5},
        headers=auth_headers(manager),
    ).json()


def _create_order(client, table, item):
    return client.post(
        "/api/v1/orders", json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]}
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


def test_scanner_le_qr_diffuse_table_occupied_au_canal_staff(client):
    """
    Remplace le sondage du plan de salle toutes les 20 s côté écran serveur
    (ROADMAP_PRODUCTION.md §P3.3, F18) : sans cette diffusion, une table tout
    juste occupée n'apparaissait qu'au prochain sondage, jusqu'à 20 s plus tard.
    """
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)

    billet = ws_billet(manager)
    with client.websocket_connect(f"/ws/staff/{restaurant.id}?billet={billet}") as ws:
        client.get(f"/api/v1/tables/by-token/{table['qr_token']}")
        message = ws.receive_json()

    assert message["event"] == "table.occupied"
    assert message["table_id"] == table["id"]
    assert message["occupied_at"] is not None


def test_un_deuxieme_scan_ne_diffuse_rien(client, db_session):
    """
    Sans cette garde, chaque rafraîchissement du menu par un client déjà
    installé rediffuserait `table.occupied` au canal staff — exactement la
    charge de fond que F18 doit faire disparaître, déplacée d'un sondage
    toutes les 20 s vers une diffusion à chaque requête.
    """
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)

    _, first = tables_service.get_table_by_qr_token_diffusing(db_session, table["qr_token"])
    assert len(first) == 1
    assert first[0].message["event"] == "table.occupied"

    _, second = tables_service.get_table_by_qr_token_diffusing(db_session, table["qr_token"])
    assert second == []


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


def test_liberer_la_table_vide_le_panier_et_le_roster(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")
    table_cart.table_cart_store.set_line(table["id"], OrderItemCreate(menu_item_id=1))
    table_roster.table_roster_store.set_name(table["id"], "device-a", "Sami")

    client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))

    assert table_cart.table_cart_store.snapshot(table["id"]) == []
    assert table_roster.table_roster_store.snapshot(table["id"]) == []


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


def test_liberer_une_table_avec_commande_en_cours_sans_note_est_refuse(client):
    """Aucune confiance faite au frontend seul : le backend recalcule
    lui-même si une commande est en cours et exige la note dans ce cas."""
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    item = _create_item(client, restaurant, manager)
    _create_order(client, table, item)  # reste PENDING_CONFIRMATION

    response = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NOTE_REQUIRED"
    assert response.json()["detail"]["order_status"] == "pending_confirmation"
    # Rien n'a été fait : la table reste occupée, personne ne doit croire
    # qu'un refus a quand même libéré la table.
    assert _occupied_at(client, restaurant, manager, table["id"]) is not None


def test_liberer_une_table_avec_commande_en_cours_et_note_est_tracee(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    table = _create_table(client, restaurant, manager)
    item = _create_item(client, restaurant, manager)
    _create_order(client, table, item)

    response = client.post(
        f"/api/v1/tables/{table['id']}/release",
        json={"note": "Client parti sans prévenir, plat pas encore en cuisine."},
        headers=auth_headers(waiter),
    )
    assert response.status_code == 200, response.text
    assert response.json()["occupied_at"] is None

    releases = client.get(
        f"/api/v1/tables/forced-releases/{restaurant.id}", headers=auth_headers(manager)
    ).json()
    assert len(releases) == 1
    assert releases[0]["table_id"] == table["id"]
    assert releases[0]["table_label"] == "Table 1"
    assert releases[0]["released_by_name"] == waiter.name
    assert releases[0]["order_status_snapshot"] == "pending_confirmation"
    assert releases[0]["note"] == "Client parti sans prévenir, plat pas encore en cuisine."


def test_liberer_une_table_sans_commande_ne_trace_rien(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    client.get(f"/api/v1/tables/by-token/{table['qr_token']}")

    response = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))

    assert response.status_code == 200, response.text
    releases = client.get(
        f"/api/v1/tables/forced-releases/{restaurant.id}", headers=auth_headers(manager)
    ).json()
    assert releases == []


def test_liberer_une_table_avec_commande_servie_et_payee_ne_trace_rien(client):
    """Terminée et payée = le seul cas sûr explicitement demandé par
    Wassim : pas de note, pas de trace, comme une libération normale."""
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    item = _create_item(client, restaurant, manager)
    order = _create_order(client, table, item)

    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/mark-served", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))
    pending = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=auth_headers(manager)
    )
    payment_id = pending.json()[0]["payment_id"]
    client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm/{payment_id}", headers=auth_headers(manager))

    response = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))

    assert response.status_code == 200, response.text
    releases = client.get(
        f"/api/v1/tables/forced-releases/{restaurant.id}", headers=auth_headers(manager)
    ).json()
    assert releases == []


def test_liberer_une_table_avec_commande_servie_non_payee_exige_une_note(client):
    """Servie mais pas encore encaissée n'est PAS "terminée et payée" — reste
    une libération en cours de commande au sens de cette fonctionnalité."""
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    item = _create_item(client, restaurant, manager)
    order = _create_order(client, table, item)

    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=auth_headers(manager))
    client.post(f"/api/v1/orders/{order['id']}/mark-served", headers=auth_headers(manager))

    refused = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))
    assert refused.status_code == 422
    assert refused.json()["detail"]["order_status"] == "served_unpaid"

    accepted = client.post(
        f"/api/v1/tables/{table['id']}/release",
        json={"note": "Parti sans payer, addition à recouvrer."},
        headers=auth_headers(manager),
    )
    assert accepted.status_code == 200, accepted.text
    releases = client.get(
        f"/api/v1/tables/forced-releases/{restaurant.id}", headers=auth_headers(manager)
    ).json()
    assert len(releases) == 1
    assert releases[0]["order_status_snapshot"] == "served_unpaid"


def test_liberer_une_table_avec_commande_annulee_ne_trace_rien(client):
    """Une commande annulée n'est pas "en cours" — comme si elle n'existait
    pas pour cette fonctionnalité."""
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    table = _create_table(client, restaurant, manager)
    item = _create_item(client, restaurant, manager)
    order = _create_order(client, table, item)
    client.post(f"/api/v1/orders/{order['id']}/cancel", headers=auth_headers(manager))

    response = client.post(f"/api/v1/tables/{table['id']}/release", headers=auth_headers(manager))

    assert response.status_code == 200, response.text
    releases = client.get(
        f"/api/v1/tables/forced-releases/{restaurant.id}", headers=auth_headers(manager)
    ).json()
    assert releases == []


def test_lister_les_liberations_forcees_est_reserve_au_manager(client):
    restaurant = create_restaurant()
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    response = client.get(f"/api/v1/tables/forced-releases/{restaurant.id}", headers=auth_headers(waiter))

    assert response.status_code == 403
