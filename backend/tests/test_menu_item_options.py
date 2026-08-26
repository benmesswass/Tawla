"""
Options et suppléments sur un article (« Cuisson », « Sauce », « Accompagnement »)
— France, MARCHE_FRANCE.md phase F5/A2, « le manque fonctionnel le plus grave » :
un steak sans cuisson ne part pas en cuisine. Indépendant de la stratégie
d'encaissement (S1/S2, phase F2), donc codable avant cet arbitrage.

Suit le gabarit de test_menu_suggestions.py : gestion manager (remplacement en
bloc), puis effet réel sur une commande (validation, prix figé, diffusion
cuisine).
"""
from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem, MenuItemOption
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _setup(db_session, slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=slug)
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    steak = MenuItem(restaurant_id=restaurant.id, name="Entrecôte", price=32.0, category="Plats")
    salade = MenuItem(restaurant_id=restaurant.id, name="Salade", price=8.0, category="Entrées")
    db_session.add_all([table, steak, salade])
    db_session.commit()
    for obj in (table, steak, salade):
        db_session.refresh(obj)
    return restaurant, table, steak, salade


def _set_groups(client, manager, item_id: int, groups: list[dict]):
    return client.put(
        f"/api/v1/menu-items/{item_id}/option-groups",
        json={"groups": groups},
        headers=auth_headers(manager),
    )


CUISSON = {
    "name": "Cuisson",
    "min_select": 1,
    "max_select": 1,
    "options": [
        {"name": "Saignant", "price_delta": 0},
        {"name": "À point", "price_delta": 0},
        {"name": "Bien cuit", "price_delta": 0},
    ],
}

SUPPLEMENTS = {
    "name": "Suppléments",
    "min_select": 0,
    "max_select": 2,
    "options": [
        {"name": "Frites", "price_delta": 3.0},
        {"name": "Sauce poivre", "price_delta": 1.5},
        {"name": "Champignons", "price_delta": 2.0},
    ],
}


# --- Gestion par le manager --------------------------------------------------


def test_manager_sets_and_replaces_option_groups(client, db_session):
    restaurant, _table, steak, _salade = _setup(db_session, "opt-set")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set_groups(client, manager, steak.id, [CUISSON, SUPPLEMENTS])
    assert response.status_code == 200
    groups = response.json()["option_groups"]
    assert [g["name"] for g in groups] == ["Cuisson", "Suppléments"]
    assert [o["name"] for o in groups[0]["options"]] == ["Saignant", "À point", "Bien cuit"]
    assert groups[1]["options"][0]["price_delta"] == 3.0

    # Remplacement en bloc, rejouable : un groupe absent du second appel disparaît.
    response = _set_groups(client, manager, steak.id, [CUISSON])
    assert [g["name"] for g in response.json()["option_groups"]] == ["Cuisson"]


def test_replacing_a_group_actually_deletes_its_old_options(client, db_session):
    """
    Régression : un remplacement en bloc par requête DELETE brute contourne le
    cascade ORM et laisse les anciennes options orphelines en base (constaté
    contre Postgres, où la contrainte de clé étrangère le refuse carrément —
    SQLite, utilisé ici, ne l'impose pas par défaut et laisserait passer une
    ligne fantôme sans ce test explicite sur la table elle-même).
    """
    restaurant, _table, steak, _salade = _setup(db_session, "opt-cascade")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    saved = _set_groups(client, manager, steak.id, [SUPPLEMENTS]).json()
    old_option_id = saved["option_groups"][0]["options"][0]["id"]

    _set_groups(client, manager, steak.id, [CUISSON])

    assert db_session.get(MenuItemOption, old_option_id) is None


def test_empty_groups_list_removes_all_options(client, db_session):
    restaurant, _table, steak, _salade = _setup(db_session, "opt-vide")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set_groups(client, manager, steak.id, [CUISSON])

    response = _set_groups(client, manager, steak.id, [])
    assert response.status_code == 200
    assert response.json()["option_groups"] == []


def test_option_groups_appear_on_the_client_menu(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-client")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set_groups(client, manager, steak.id, [CUISSON])

    menu = client.get(f"/api/v1/menu-items/by-table/{table.qr_token}").json()
    item = next(i for i in menu if i["id"] == steak.id)
    assert [g["name"] for g in item["option_groups"]] == ["Cuisson"]


def test_min_select_above_max_select_is_rejected(client, db_session):
    restaurant, _table, steak, _salade = _setup(db_session, "opt-minmax")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    bad = {**CUISSON, "min_select": 2, "max_select": 1}
    assert _set_groups(client, manager, steak.id, [bad]).status_code == 422


def test_group_without_options_is_rejected(client, db_session):
    restaurant, _table, steak, _salade = _setup(db_session, "opt-sansoption")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    bad = {"name": "Vide", "min_select": 0, "max_select": 1, "options": []}
    assert _set_groups(client, manager, steak.id, [bad]).status_code == 422


def test_setting_option_groups_is_manager_only(client, db_session):
    restaurant, _table, steak, _salade = _setup(db_session, "opt-role")
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    assert _set_groups(client, waiter, steak.id, [CUISSON]).status_code == 403
    assert client.put(
        f"/api/v1/menu-items/{steak.id}/option-groups", json={"groups": [CUISSON]}
    ).status_code == 401


def test_cannot_set_option_groups_on_another_restaurants_item(client, db_session):
    restaurant, _t, steak, _s = _setup(db_session, "opt-iso-a")
    _other, _t2, other_steak, _s2 = _setup(db_session, "opt-iso-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set_groups(client, manager, other_steak.id, [CUISSON])
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ITEM_NOT_FOUND"


# --- Effet sur la commande ---------------------------------------------------


def _order_payload(table, item, selected_option_ids=None, quantity=1):
    return {
        "qr_token": table.qr_token,
        "items": [
            {
                "menu_item_id": item.id,
                "quantity": quantity,
                "selected_option_ids": selected_option_ids or [],
            }
        ],
    }


def test_required_group_blocks_order_when_nothing_selected(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-requis")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set_groups(client, manager, steak.id, [CUISSON])

    response = client.post("/api/v1/orders", json=_order_payload(table, steak))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_OPTION_SELECTION"
    assert response.json()["detail"]["group_name"] == "Cuisson"


def test_valid_selection_freezes_price_and_names_on_the_order(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-prix")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    saved = _set_groups(client, manager, steak.id, [CUISSON, SUPPLEMENTS]).json()
    a_point_id = next(o["id"] for o in saved["option_groups"][0]["options"] if o["name"] == "À point")
    frites_id = next(o["id"] for o in saved["option_groups"][1]["options"] if o["name"] == "Frites")

    response = client.post(
        "/api/v1/orders", json=_order_payload(table, steak, [a_point_id, frites_id], quantity=2)
    )
    assert response.status_code == 201
    item = response.json()["items"][0]
    # 32.0 (base) + 0 (cuisson) + 3.0 (frites) = 35.0, la quantité ne joue que
    # sur le total, jamais sur unit_price.
    assert item["unit_price"] == 35.0
    assert response.json()["total_amount"] == 70.0
    options = {o["option_name"]: o["price_delta"] for o in item["options"]}
    assert options == {"À point": 0.0, "Frites": 3.0}
    assert {o["group_name"] for o in item["options"]} == {"Cuisson", "Suppléments"}


def test_too_many_selections_in_a_group_is_rejected(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-trop")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    saved = _set_groups(client, manager, steak.id, [SUPPLEMENTS]).json()
    ids = [o["id"] for o in saved["option_groups"][0]["options"]]  # 3 options, max_select=2

    response = client.post("/api/v1/orders", json=_order_payload(table, steak, ids))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_OPTION_SELECTION"


def test_optional_group_can_be_skipped(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-optionnel")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set_groups(client, manager, steak.id, [SUPPLEMENTS])

    response = client.post("/api/v1/orders", json=_order_payload(table, steak))
    assert response.status_code == 201
    assert response.json()["items"][0]["unit_price"] == 32.0
    assert response.json()["items"][0]["options"] == []


def test_option_id_from_another_item_is_rejected(client, db_session):
    restaurant, table, steak, salade = _setup(db_session, "opt-autre-article")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set_groups(client, manager, steak.id, [CUISSON])
    salade_groups = _set_groups(
        client, manager, salade.id,
        [{"name": "Assaisonnement", "min_select": 0, "max_select": 1, "options": [{"name": "Citron", "price_delta": 0}]}],
    ).json()
    citron_id = salade_groups["option_groups"][0]["options"][0]["id"]

    # L'id de l'option "Citron" appartient à la salade, pas à l'entrecôte.
    response = client.post("/api/v1/orders", json=_order_payload(table, steak, [citron_id]))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "OPTION_NOT_FOUND"


def test_unknown_option_id_is_rejected(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-inconnu")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set_groups(client, manager, steak.id, [CUISSON])

    response = client.post("/api/v1/orders", json=_order_payload(table, steak, [999999]))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "OPTION_NOT_FOUND"


def test_editing_options_later_never_changes_a_past_order(client, db_session):
    """Même principe que le prix figé sur OrderItem : une commande passée ne
    doit jamais bouger si le manager modifie la carte après coup."""
    restaurant, table, steak, _salade = _setup(db_session, "opt-fige")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    saved = _set_groups(client, manager, steak.id, [CUISSON]).json()
    a_point_id = next(o["id"] for o in saved["option_groups"][0]["options"] if o["name"] == "À point")

    order = client.post("/api/v1/orders", json=_order_payload(table, steak, [a_point_id])).json()

    # Le manager retire "À point" et remplace tout le groupe.
    _set_groups(client, manager, steak.id, [{**CUISSON, "options": [{"name": "Saignant", "price_delta": 5.0}]}])

    reread = client.get(f"/api/v1/orders/{order['id']}", headers={"X-Order-Token": order["public_token"]}).json()
    assert reread["items"][0]["options"] == [{"group_name": "Cuisson", "option_name": "À point", "price_delta": 0.0}]
    assert reread["items"][0]["unit_price"] == 32.0


def test_kitchen_broadcast_carries_the_selected_options(client, db_session):
    restaurant, table, steak, _salade = _setup(db_session, "opt-cuisine")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    saved = _set_groups(client, manager, steak.id, [CUISSON]).json()
    saignant_id = next(o["id"] for o in saved["option_groups"][0]["options"] if o["name"] == "Saignant")
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    kitchen_token = auth_headers(kitchen)["Authorization"].split()[1]

    order = client.post("/api/v1/orders", json=_order_payload(table, steak, [saignant_id])).json()
    client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(waiter))
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(waiter))

    with client.websocket_connect(f"/ws/kitchen/{restaurant.id}?token={kitchen_token}") as ws:
        client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(waiter))
        msg = ws.receive_json()
        assert msg["event"] == "order.sent_to_kitchen"
        assert msg["items"][0]["options"] == [{"group_name": "Cuisson", "option_name": "Saignant"}]
