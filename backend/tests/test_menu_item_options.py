"""
Options et suppléments sur un article (F5-A2, MARCHE_FRANCE.md).

Le manque fonctionnel le plus grave identifié pour le marché français :
jusqu'ici, un article ne portait qu'une note en texte libre — un steak sans
cuisson précisée ne part pas en cuisine en France.

Le prix, comme partout ailleurs dans ce produit, est toujours recalculé côté
serveur : ces tests vérifient d'abord que le client ne peut ni inventer un
choix, ni ignorer un groupe requis, ni doubler un groupe à choix unique.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup_item_with_options(client):
    restaurant = create_restaurant(name="Le Central", slug="le-central-options")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Entrecôte", "price": 18.0},
        headers=headers,
    ).json()
    item = client.put(
        f"/api/v1/menu-items/{item['id']}/options",
        json={
            "groups": [
                {
                    "name": "Cuisson",
                    "is_required": True,
                    "allow_multiple": False,
                    "choices": [
                        {"name": "Saignant", "price_delta": 0},
                        {"name": "À point", "price_delta": 0},
                    ],
                },
                {
                    "name": "Accompagnement",
                    "is_required": False,
                    "allow_multiple": True,
                    "choices": [
                        {"name": "Frites", "price_delta": 0},
                        {"name": "Salade", "price_delta": 0},
                        {"name": "Supplément fromage", "price_delta": 1.5},
                    ],
                },
            ]
        },
        headers=headers,
    ).json()
    return restaurant, table, item, headers


def test_manager_sets_option_groups_and_they_appear_on_the_item(client):
    _restaurant, _table, item, _headers = _setup_item_with_options(client)
    assert len(item["option_groups"]) == 2
    cuisson = next(g for g in item["option_groups"] if g["name"] == "Cuisson")
    assert cuisson["is_required"] is True
    assert cuisson["allow_multiple"] is False
    assert {c["name"] for c in cuisson["choices"]} == {"Saignant", "À point"}


def test_manager_cannot_set_options_on_another_restaurants_item(client):
    _restaurant, _table, item, _headers = _setup_item_with_options(client)
    other = create_restaurant(name="Ailleurs", slug="ailleurs-options")
    other_headers = auth_headers(create_staff(other.id))

    res = client.put(f"/api/v1/menu-items/{item['id']}/options", json={"groups": []}, headers=other_headers)
    assert res.status_code == 404


def test_order_with_valid_options_computes_the_right_price_and_freezes_choices(client):
    restaurant, table, item, headers = _setup_item_with_options(client)
    cuisson_choice = next(c for g in item["option_groups"] if g["name"] == "Cuisson" for c in g["choices"] if c["name"] == "Saignant")
    fromage_choice = next(
        c for g in item["option_groups"] if g["name"] == "Accompagnement" for c in g["choices"] if c["name"] == "Supplément fromage"
    )

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [
                {
                    "menu_item_id": item["id"],
                    "quantity": 1,
                    "selected_choice_ids": [cuisson_choice["id"], fromage_choice["id"]],
                }
            ],
        },
    ).json()

    line = order["items"][0]
    assert line["unit_price"] == 19.5  # 18.0 + 1.5
    assert {o["choice_name"] for o in line["selected_options"]} == {"Saignant", "Supplément fromage"}


def test_order_rejects_a_missing_required_group(client):
    _restaurant, table, item, _headers = _setup_item_with_options(client)

    res = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "OPTION_GROUP_REQUIRED"


def test_order_rejects_two_choices_in_a_single_choice_group(client):
    _restaurant, table, item, _headers = _setup_item_with_options(client)
    cuisson = next(g for g in item["option_groups"] if g["name"] == "Cuisson")
    both_ids = [c["id"] for c in cuisson["choices"]]

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1, "selected_choice_ids": both_ids}],
        },
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "OPTION_GROUP_SINGLE_CHOICE"


def test_order_rejects_a_choice_that_belongs_to_another_item(client):
    restaurant, table, item, headers = _setup_item_with_options(client)
    other_item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Salade César", "price": 9.0},
        headers=headers,
    ).json()
    other_item = client.put(
        f"/api/v1/menu-items/{other_item['id']}/options",
        json={"groups": [{"name": "Taille", "choices": [{"name": "Grande", "price_delta": 2}]}]},
        headers=headers,
    ).json()
    foreign_choice_id = other_item["option_groups"][0]["choices"][0]["id"]

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [
                {
                    "menu_item_id": item["id"],
                    "quantity": 1,
                    "selected_choice_ids": [foreign_choice_id],
                }
            ],
        },
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] in ("INVALID_OPTION_CHOICE", "OPTION_GROUP_REQUIRED")


def test_replacing_option_groups_does_not_change_an_already_placed_order(client):
    """Même principe que le prix figé sur `OrderItem` (CLAUDE.md) : une
    commande déjà passée ne doit jamais bouger si la carte change ensuite."""
    restaurant, table, item, headers = _setup_item_with_options(client)
    cuisson_choice = next(c for g in item["option_groups"] if g["name"] == "Cuisson" for c in g["choices"] if c["name"] == "Saignant")

    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1, "selected_choice_ids": [cuisson_choice["id"]]}],
        },
    ).json()
    assert order["items"][0]["selected_options"][0]["choice_name"] == "Saignant"

    # Le manager renomme le groupe et retire le choix — la commande déjà
    # passée doit garder "Saignant" tel quel.
    client.put(
        f"/api/v1/menu-items/{item['id']}/options",
        json={"groups": [{"name": "Cuisson (v2)", "choices": [{"name": "Bleu"}]}]},
        headers=headers,
    )

    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=order_headers(order)).json()
    assert fetched["items"][0]["selected_options"][0]["choice_name"] == "Saignant"
