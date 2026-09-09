"""
Convives déclarés à une table (`ROADMAP.md` §Override — panier synchronisé
multi-appareils, extension) : nombre de personnes + prénoms facultatifs,
partagés en temps réel sur le même canal `/ws/table/...` que le panier.
Purement déclaratif — sert seulement à l'affichage (calculateur d'addition).
"""

from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant_with_table(client, slug):
    restaurant = create_restaurant(name="Dar Chaabane", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    return restaurant, table


def _connect(client, restaurant, table):
    return client.websocket_connect(f"/ws/table/{restaurant.id}/{table['qr_token']}")


def _skip_cart_snapshot(ws):
    ws.receive_json()  # cart.updated, vide — pas l'objet de ce test


def test_declarer_les_convives_est_diffuse_en_temps_reel(client):
    restaurant, table = _setup_restaurant_with_table(client, "party-live")

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        _skip_cart_snapshot(ws_a)
        _skip_cart_snapshot(ws_b)
        assert ws_a.receive_json() == {"event": "party.updated", "size": None, "names": []}
        assert ws_b.receive_json() == {"event": "party.updated", "size": None, "names": []}

        ws_a.send_json({"action": "party.set", "size": 2, "names": ["Ahmed", ""]})
        expected = {"event": "party.updated", "size": 2, "names": ["Ahmed", None]}
        assert ws_a.receive_json() == expected
        assert ws_b.receive_json() == expected


def test_un_appareil_qui_rejoint_voit_les_convives_deja_declares(client):
    restaurant, table = _setup_restaurant_with_table(client, "party-join")

    with _connect(client, restaurant, table) as ws_a:
        _skip_cart_snapshot(ws_a)
        ws_a.receive_json()  # party.updated initial, vide
        ws_a.send_json({"action": "party.set", "size": 3, "names": ["Sami", None, "Wassim"]})
        ws_a.receive_json()  # écho

        with _connect(client, restaurant, table) as ws_b:
            _skip_cart_snapshot(ws_b)
            assert ws_b.receive_json() == {
                "event": "party.updated", "size": 3, "names": ["Sami", None, "Wassim"],
            }


def test_la_taille_est_bornee_et_les_prenoms_ajustes_a_la_taille(client):
    restaurant, table = _setup_restaurant_with_table(client, "party-bounds")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_snapshot(ws)
        ws.receive_json()

        # Trop de prénoms pour la taille demandée : tronqués, pas rejetés.
        ws.send_json({"action": "party.set", "size": 2, "names": ["A", "B", "C"]})
        assert ws.receive_json() == {"event": "party.updated", "size": 2, "names": ["A", "B"]}

        # Taille au-delà de la borne haute : ramenée à la borne, jamais une erreur
        # pour une saisie qui n'a rien de dangereux, juste absurde.
        ws.send_json({"action": "party.set", "size": 999, "names": ["Seul"]})
        message = ws.receive_json()
        assert message["event"] == "party.updated"
        assert message["size"] == 20
        assert len(message["names"]) == 20
        assert message["names"][0] == "Seul"


def test_les_convives_survivent_a_une_deconnexion(client):
    """
    2026-09-09 (demande de Wassim) : plus aucune déconnexion ne doit vider la
    déclaration — les clients doivent pouvoir la garder tant qu'ils sont à
    table, quelle que soit la durée passée sans appareil connecté. Seul le
    bouton « Libérer la table » du serveur/manager la vide désormais (voir
    `test_tables_release.py`).
    """
    restaurant, table = _setup_restaurant_with_table(client, "party-clear")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_snapshot(ws)
        ws.receive_json()
        ws.send_json({"action": "party.set", "size": 4, "names": ["Ahmed", None, None, None]})
        ws.receive_json()

    with _connect(client, restaurant, table) as ws_after:
        _skip_cart_snapshot(ws_after)
        assert ws_after.receive_json() == {
            "event": "party.updated", "size": 4, "names": ["Ahmed", None, None, None],
        }


def test_convives_isoles_entre_deux_tables(client):
    restaurant, table_a = _setup_restaurant_with_table(client, "party-iso-a")
    headers = auth_headers(create_staff(restaurant.id))
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 2"}, headers=headers
    ).json()

    with _connect(client, restaurant, table_a) as ws_a, _connect(client, restaurant, table_b) as ws_b:
        _skip_cart_snapshot(ws_a)
        _skip_cart_snapshot(ws_b)
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"action": "party.set", "size": 5, "names": ["Ahmed"]})
        ws_a.receive_json()

        # Table B n'a rien vu passer de la déclaration de A.
        ws_b.send_json({"action": "party.set", "size": 1, "names": []})
        assert ws_b.receive_json() == {"event": "party.updated", "size": 1, "names": [None]}
