"""
Formules — entrée + plat + dessert (F5-A3, MARCHE_FRANCE.md).

Le produit dominant du déjeuner français (§3.2) : un prix fixe pour un repas
composé d'un choix par étape, toujours inférieur à la somme des prix normaux
des articles pris séparément. Ces tests vérifient d'abord que le prix reste
TOUJOURS celui de la formule (jamais recalculé depuis les articles choisis),
et que le client ne peut ni inventer un choix, ni sauter une étape, ni en
doubler une.
"""
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup_formula(client):
    restaurant = create_restaurant(name="Le Central", slug="le-central-formules")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()

    def _item(name, price):
        return client.post(
            "/api/v1/menu-items",
            json={"restaurant_id": restaurant.id, "name": name, "price": price},
            headers=headers,
        ).json()

    salade = _item("Salade César", 8.0)
    soupe = _item("Soupe du jour", 6.0)
    entrecote = _item("Entrecôte", 18.0)
    saumon = _item("Saumon", 16.0)
    tarte = _item("Tarte tatin", 7.0)

    formula = client.post(
        "/api/v1/menu-formulas",
        json={
            "restaurant_id": restaurant.id,
            "name": "Formule Midi",
            "price": 22.0,
            "slots": [
                {"name": "Entrée", "item_ids": [salade["id"], soupe["id"]]},
                {"name": "Plat", "item_ids": [entrecote["id"], saumon["id"]]},
                {"name": "Dessert", "item_ids": [tarte["id"]]},
            ],
        },
        headers=headers,
    ).json()
    return restaurant, table, formula, headers, {
        "salade": salade, "soupe": soupe, "entrecote": entrecote, "saumon": saumon, "tarte": tarte,
    }


def test_manager_creates_a_formula_and_it_appears_with_its_slots(client):
    _restaurant, _table, formula, _headers, _items = _setup_formula(client)
    assert formula["name"] == "Formule Midi"
    assert formula["price"] == 22.0
    assert len(formula["slots"]) == 3
    entree = next(s for s in formula["slots"] if s["name"] == "Entrée")
    assert {i["name"] for i in entree["items"]} == {"Salade César", "Soupe du jour"}


def test_manager_cannot_compose_a_formula_with_another_restaurants_items(client):
    _restaurant, _table, _formula, headers, _items = _setup_formula(client)
    other = create_restaurant(name="Ailleurs", slug="ailleurs-formules")
    other_headers = auth_headers(create_staff(other.id))
    other_item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": other.id, "name": "Plat d'ailleurs", "price": 10.0},
        headers=other_headers,
    ).json()

    res = client.post(
        "/api/v1/menu-formulas",
        json={
            "restaurant_id": _restaurant.id,
            "name": "Formule piégée",
            "price": 15.0,
            "slots": [{"name": "Plat", "item_ids": [other_item["id"]]}],
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "INVALID_FORMULA_SLOT_ITEM"


def test_manager_cannot_update_another_restaurants_formula(client):
    _restaurant, _table, formula, _headers, _items = _setup_formula(client)
    other = create_restaurant(name="Ailleurs 2", slug="ailleurs-formules-2")
    other_headers = auth_headers(create_staff(other.id))

    res = client.put(
        f"/api/v1/menu-formulas/{formula['id']}",
        json={"name": "Volée", "price": 1.0, "slots": [{"name": "Plat", "item_ids": [1]}]},
        headers=other_headers,
    )
    assert res.status_code == 404


def test_order_with_a_valid_formula_selection_charges_the_fixed_price(client):
    restaurant, table, formula, _headers, items = _setup_formula(client)

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["soupe"]["id"], items["entrecote"]["id"], items["tarte"]["id"]],
                }
            ],
        },
    ).json()

    line = order["formulas"][0]
    # 22.0, jamais 6.0 + 18.0 + 7.0 = 31.0 : c'est tout l'intérêt commercial
    # d'une formule.
    assert line["unit_price"] == 22.0
    assert order["total_amount"] == 22.0
    assert {s["menu_item_name"] for s in line["selections"]} == {"Soupe du jour", "Entrecôte", "Tarte tatin"}
    slot_names = {s["slot_name"] for s in line["selections"]}
    assert slot_names == {"Entrée", "Plat", "Dessert"}


def test_order_mixes_items_and_formulas_and_sums_both(client):
    restaurant, table, formula, headers, items = _setup_formula(client)
    coca = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Coca", "price": 3.5},
        headers=headers,
    ).json()

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": coca["id"], "quantity": 2}],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["salade"]["id"], items["saumon"]["id"], items["tarte"]["id"]],
                }
            ],
        },
    ).json()

    assert order["total_amount"] == 22.0 + 2 * 3.5


def test_order_rejects_a_formula_missing_a_slot_choice(client):
    _restaurant, table, formula, _headers, items = _setup_formula(client)

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["salade"]["id"], items["entrecote"]["id"]],
                }
            ],
        },
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "FORMULA_SLOT_REQUIRES_ONE_CHOICE"


def test_order_rejects_two_choices_for_the_same_slot(client):
    _restaurant, table, formula, _headers, items = _setup_formula(client)

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [
                        items["salade"]["id"],
                        items["soupe"]["id"],
                        items["entrecote"]["id"],
                        items["tarte"]["id"],
                    ],
                }
            ],
        },
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "FORMULA_SLOT_REQUIRES_ONE_CHOICE"


def test_order_rejects_an_item_that_does_not_belong_to_the_formula(client):
    restaurant, table, formula, headers, items = _setup_formula(client)
    outsider = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Plat hors formule", "price": 12.0},
        headers=headers,
    ).json()

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["salade"]["id"], outsider["id"], items["tarte"]["id"]],
                }
            ],
        },
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "INVALID_FORMULA_ITEM"


def test_order_rejects_an_unavailable_formula(client):
    restaurant, table, formula, headers, items = _setup_formula(client)
    client.put(
        f"/api/v1/menu-formulas/{formula['id']}",
        json={
            "name": formula["name"],
            "price": formula["price"],
            "is_available": False,
            "slots": [{"name": s["name"], "item_ids": [i["id"] for i in s["items"]]} for s in formula["slots"]],
        },
        headers=headers,
    )

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["salade"]["id"], items["entrecote"]["id"], items["tarte"]["id"]],
                }
            ],
        },
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "FORMULA_UNAVAILABLE"


def test_replacing_formula_slots_does_not_change_an_already_placed_order(client):
    """Même principe que le prix figé sur `OrderItem` (CLAUDE.md) : une
    commande déjà passée ne doit jamais bouger si la carte change ensuite."""
    restaurant, table, formula, headers, items = _setup_formula(client)

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["salade"]["id"], items["entrecote"]["id"], items["tarte"]["id"]],
                }
            ],
        },
    ).json()
    assert order["formulas"][0]["unit_price"] == 22.0

    # Le manager change le prix et retire un article — la commande déjà
    # passée doit garder son prix et ses choix tels quels.
    client.put(
        f"/api/v1/menu-formulas/{formula['id']}",
        json={
            "name": "Formule Midi (v2)",
            "price": 26.0,
            "slots": [{"name": "Plat", "item_ids": [items["saumon"]["id"]]}],
        },
        headers=headers,
    )

    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=order_headers(order)).json()
    assert fetched["formulas"][0]["unit_price"] == 22.0
    assert {s["menu_item_name"] for s in fetched["formulas"][0]["selections"]} == {
        "Salade César", "Entrecôte", "Tarte tatin",
    }


def test_empty_order_without_items_or_formulas_is_rejected(client):
    _restaurant, table, _formula, _headers, _items = _setup_formula(client)

    res = client.post("/api/v1/orders", json={"qr_token": table["qr_token"], "items": [], "formulas": []})
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "EMPTY_ORDER"


def test_kitchen_websocket_broadcast_carries_the_formula_and_its_selections(client):
    restaurant, table, formula, headers, items = _setup_formula(client)
    kitchen_staff = create_staff(restaurant.id, StaffRole.KITCHEN)

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "formulas": [
                {
                    "formula_id": formula["id"],
                    "quantity": 1,
                    "selected_item_ids": [items["soupe"]["id"], items["entrecote"]["id"], items["tarte"]["id"]],
                }
            ],
        },
    ).json()

    with client.websocket_connect(
        f"/ws/kitchen/{restaurant.id}?token={auth_headers(kitchen_staff)['Authorization'].split()[1]}"
    ) as ws:
        client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers)
        client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=headers)
        message = ws.receive_json()

    formula_ticket_line = next(it for it in message["items"] if it["name"] == "Formule Midi")
    assert set(formula_ticket_line["options"].split(", ")) == {"Soupe du jour", "Entrecôte", "Tarte tatin"}
