"""
Panier synchronisé multi-appareils (`ROADMAP.md` §Override) : plusieurs
téléphones connectés au canal `/ws/table/...` de la même table partagent un
panier tenu en mémoire côté serveur (`orders/table_cart.py`) et valident une
seule commande pour la table entière.
"""

from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_item(client, available=True, price=3.5):
    restaurant = create_restaurant(name="Café Test", slug=f"cafe-test-cart-{price}")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Café", "price": price},
        headers=headers,
    ).json()
    if not available:
        client.patch(f"/api/v1/menu-items/{item['id']}/availability", json={"is_available": False}, headers=headers)
    return restaurant, table, item, headers


def _connect(client, restaurant, table):
    return client.websocket_connect(f"/ws/table/{restaurant.id}/{table['qr_token']}")


def _skip_party_snapshot(ws) -> None:
    """Deuxième message envoyé à la connexion (convives déclarés) — hors
    sujet de ce fichier, voir test_table_party.py."""
    ws.receive_json()


def test_deux_appareils_composent_le_meme_panier_en_temps_reel(client):
    restaurant, table, item, _headers = _setup_restaurant_with_item(client)

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        assert ws_a.receive_json() == {"event": "cart.updated", "lines": []}
        _skip_party_snapshot(ws_a)
        assert ws_b.receive_json() == {"event": "cart.updated", "lines": []}
        _skip_party_snapshot(ws_b)

        ws_a.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 2})
        expected = {
            "event": "cart.updated",
            "lines": [
                {
                    "menu_item_id": item["id"], "quantity": 2, "notes": None, "is_shared": False,
                    "shared_with": [], "from_suggestion": False, "selected_option_ids": [],
                }
            ],
        }
        # Diffusé à TOUS les appareils connectés, y compris celui qui vient
        # d'émettre la mutation : le serveur est la seule source de vérité,
        # aucun appareil n'applique sa propre écriture en local.
        assert ws_a.receive_json() == expected
        assert ws_b.receive_json() == expected

        # Un deuxième convive ajoute un article différent depuis SON appareil.
        ws_b.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 0})
        cleared = {"event": "cart.updated", "lines": []}
        assert ws_a.receive_json() == cleared
        assert ws_b.receive_json() == cleared


def test_un_appareil_qui_rejoint_voit_deja_ce_que_les_autres_ont_ajoute(client):
    restaurant, table, item, _headers = _setup_restaurant_with_item(client)

    with _connect(client, restaurant, table) as ws_a:
        ws_a.receive_json()  # snapshot initial, vide
        _skip_party_snapshot(ws_a)
        ws_a.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 1})
        ws_a.receive_json()  # écho de sa propre mutation

        with _connect(client, restaurant, table) as ws_b:
            snapshot = ws_b.receive_json()
            _skip_party_snapshot(ws_b)
            assert snapshot["lines"] == [
                {
                    "menu_item_id": item["id"], "quantity": 1, "notes": None, "is_shared": False,
                    "shared_with": [], "from_suggestion": False, "selected_option_ids": [],
                }
            ]


def test_nimporte_quel_appareil_peut_valider_pour_toute_la_table(client):
    restaurant, table, item, headers = _setup_restaurant_with_item(client)

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        ws_a.receive_json()
        _skip_party_snapshot(ws_a)
        ws_b.receive_json()
        _skip_party_snapshot(ws_b)

        ws_a.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 1})
        ws_a.receive_json()
        ws_b.receive_json()

        # C'est B qui valide, alors que c'est A qui a composé le panier.
        ws_b.send_json({"action": "cart.validate"})
        validated_a = ws_a.receive_json()
        validated_b = ws_b.receive_json()

    assert validated_a == validated_b
    assert validated_a["event"] == "cart.validated"
    order_id = validated_a["order_id"]

    order = client.get(
        f"/api/v1/orders/{order_id}", headers={"X-Order-Token": validated_a["public_token"]}
    ).json()
    assert len(order["items"]) == 1
    assert order["items"][0]["menu_item_id"] == item["id"]
    assert order["table_id"] == table["id"]

    # Le panier est vidé pour tout le monde : un nouvel appareil qui se
    # connecte ne voit plus ce qui vient d'être commandé.
    with _connect(client, restaurant, table) as ws_c:
        assert ws_c.receive_json() == {"event": "cart.updated", "lines": []}


def test_valider_un_panier_vide_ne_cree_aucune_commande(client):
    restaurant, table, _item, headers = _setup_restaurant_with_item(client)

    with _connect(client, restaurant, table) as ws:
        ws.receive_json()
        _skip_party_snapshot(ws)
        ws.send_json({"action": "cart.validate"})
        error = ws.receive_json()

    assert error == {"event": "cart.error", "code": "EMPTY_ORDER", "message": "order must contain at least one item"}

    active = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=headers).json()
    assert active == []


def test_un_article_indisponible_est_refuse_sans_corrompre_le_panier(client):
    restaurant, table, item, headers = _setup_restaurant_with_item(client, available=False)

    with _connect(client, restaurant, table) as ws:
        ws.receive_json()
        _skip_party_snapshot(ws)
        ws.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 1})
        error = ws.receive_json()
        assert error["event"] == "cart.error"
        assert error["code"] == "ITEM_UNAVAILABLE"

        with _connect(client, restaurant, table) as ws_b:
            # L'article refusé n'est jamais entré dans l'état partagé.
            assert ws_b.receive_json() == {"event": "cart.updated", "lines": []}


def test_devenir_indisponible_apres_ajout_ne_perd_pas_le_panier_des_autres(client):
    """
    Un article rendu indisponible entre l'ajout et la validation ne doit
    jamais faire disparaître silencieusement ce que les AUTRES convives ont
    mis dans le panier partagé.
    """
    restaurant, table, item, headers = _setup_restaurant_with_item(client, available=True)

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        ws_a.receive_json()
        _skip_party_snapshot(ws_a)
        ws_b.receive_json()
        _skip_party_snapshot(ws_b)

        ws_a.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 1})
        ws_a.receive_json()
        ws_b.receive_json()

        client.patch(f"/api/v1/menu-items/{item['id']}/availability", json={"is_available": False}, headers=headers)

        ws_b.send_json({"action": "cart.validate"})

        # Le panier restauré est rediffusé à TOUT le monde en premier — avec
        # l'article toujours dedans, pas perdu — puis, seulement ensuite,
        # l'appareil qui a tenté de valider reçoit en plus l'explication de
        # l'échec, lui seul.
        restored_a = ws_a.receive_json()
        restored_b = ws_b.receive_json()
        assert restored_a == restored_b
        assert restored_a["lines"][0]["menu_item_id"] == item["id"]

        error = ws_b.receive_json()
        assert error["event"] == "cart.error"
        assert error["code"] == "ITEM_UNAVAILABLE"


def test_paniers_isoles_entre_deux_tables(client):
    restaurant, table_a, item, headers = _setup_restaurant_with_item(client)
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 2"}, headers=headers
    ).json()

    with _connect(client, restaurant, table_a) as ws_a, _connect(client, restaurant, table_b) as ws_b:
        ws_a.receive_json()
        _skip_party_snapshot(ws_a)
        ws_b.receive_json()
        _skip_party_snapshot(ws_b)

        ws_a.send_json({"action": "cart.set", "menu_item_id": item["id"], "quantity": 1})
        ws_a.receive_json()

        ws_b.send_json({"action": "cart.validate"})
        error = ws_b.receive_json()
        assert error == {
            "event": "cart.error", "code": "EMPTY_ORDER", "message": "order must contain at least one item",
        }


def test_paniers_isoles_entre_deux_restaurants(client):
    restaurant_a, table_a, item_a, _headers_a = _setup_restaurant_with_item(client, price=4.0)
    restaurant_b, table_b, _item_b, _headers_b = _setup_restaurant_with_item(client, price=5.0)

    with _connect(client, restaurant_a, table_a) as ws_a, _connect(client, restaurant_b, table_b) as ws_b:
        ws_a.receive_json()
        _skip_party_snapshot(ws_a)
        ws_b.receive_json()
        _skip_party_snapshot(ws_b)

        ws_a.send_json({"action": "cart.set", "menu_item_id": item_a["id"], "quantity": 1})
        ws_a.receive_json()

        # Le même identifiant d'article, valide chez A, n'existe pas chez B.
        ws_b.send_json({"action": "cart.set", "menu_item_id": item_a["id"], "quantity": 1})
        error = ws_b.receive_json()
        assert error["event"] == "cart.error"
        assert error["code"] == "ITEM_NOT_FOUND"
