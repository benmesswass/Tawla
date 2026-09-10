"""
Qui commande à une table, et sous quel prénom (`ROADMAP.md` §Override —
identité de table, remplace l'ancien "party" : nombre de convives + prénoms
déclarés d'un coup par un seul appareil). Chaque appareil annonce son propre
prénom sous sa propre clé, en temps réel sur le même canal `/ws/table/...`
que le panier. Purement déclaratif — sert seulement à l'affichage (tag sous
le plat, calculateur d'addition).
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


def _skip_split_mode_snapshot(ws):
    """Troisième message envoyé à la connexion (mode de répartition de
    l'addition) — hors sujet de ce fichier, voir test_table_split_mode.py."""
    ws.receive_json()


def test_un_appareil_annonce_son_prenom_et_cest_diffuse_en_temps_reel(client):
    restaurant, table = _setup_restaurant_with_table(client, "roster-live")

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        _skip_cart_snapshot(ws_a)
        _skip_cart_snapshot(ws_b)
        assert ws_a.receive_json() == {"event": "roster.updated", "people": []}
        assert ws_b.receive_json() == {"event": "roster.updated", "people": []}
        _skip_split_mode_snapshot(ws_a)
        _skip_split_mode_snapshot(ws_b)

        ws_a.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        expected = {"event": "roster.updated", "people": [{"key": "device-a", "name": "Ahmed"}]}
        assert ws_a.receive_json() == expected
        assert ws_b.receive_json() == expected


def test_un_deuxieme_appareil_najoute_pas_ecrase_le_premier(client):
    """Le bug que corrige ce chantier par rapport à l'ancien `party.set` :
    deux téléphones qui répondent l'un après l'autre gardent chacun leur
    prénom, aucun des deux ne perd le sien."""
    restaurant, table = _setup_restaurant_with_table(client, "roster-additive")

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        _skip_cart_snapshot(ws_a)
        _skip_cart_snapshot(ws_b)
        ws_a.receive_json()
        ws_b.receive_json()
        _skip_split_mode_snapshot(ws_a)
        _skip_split_mode_snapshot(ws_b)

        ws_a.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        ws_a.receive_json()
        ws_b.receive_json()

        ws_b.send_json({"action": "identity.set", "device_key": "device-b", "name": "Sami"})
        expected = {
            "event": "roster.updated",
            "people": [{"key": "device-a", "name": "Ahmed"}, {"key": "device-b", "name": "Sami"}],
        }
        assert ws_a.receive_json() == expected
        assert ws_b.receive_json() == expected


def test_prenom_laisse_vide_devient_perso_suivi_du_numero_de_place(client):
    restaurant, table = _setup_restaurant_with_table(client, "roster-default-name")

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        _skip_cart_snapshot(ws_a)
        _skip_cart_snapshot(ws_b)
        ws_a.receive_json()
        ws_b.receive_json()
        _skip_split_mode_snapshot(ws_a)
        _skip_split_mode_snapshot(ws_b)

        ws_a.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        ws_a.receive_json()
        ws_b.receive_json()

        ws_b.send_json({"action": "identity.set", "device_key": "device-b", "name": ""})
        message = ws_b.receive_json()
        assert message["people"][1] == {"key": "device-b", "name": "Perso2"}


def test_reconnexion_avec_la_meme_cle_met_a_jour_sans_ajouter_une_place(client):
    restaurant, table = _setup_restaurant_with_table(client, "roster-reclaim")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_snapshot(ws)
        ws.receive_json()
        _skip_split_mode_snapshot(ws)
        ws.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        ws.receive_json()

        # Rafraîchissement de page : même clé, prénom éventuellement corrigé —
        # une seule entrée dans le roster, jamais deux.
        ws.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed 2"})
        message = ws.receive_json()
        assert message == {"event": "roster.updated", "people": [{"key": "device-a", "name": "Ahmed 2"}]}


def test_ajouter_un_convive_qui_ne_scanne_pas(client):
    restaurant, table = _setup_restaurant_with_table(client, "roster-guest")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_snapshot(ws)
        ws.receive_json()
        _skip_split_mode_snapshot(ws)
        ws.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        ws.receive_json()

        ws.send_json({"action": "identity.add_guest", "name": "Sami"})
        message = ws.receive_json()
        assert message["people"][0] == {"key": "device-a", "name": "Ahmed"}
        assert message["people"][1]["name"] == "Sami"
        assert message["people"][1]["key"].startswith("guest:")


def test_un_appareil_qui_rejoint_voit_le_roster_deja_declare(client):
    restaurant, table = _setup_restaurant_with_table(client, "roster-join")

    with _connect(client, restaurant, table) as ws_a:
        _skip_cart_snapshot(ws_a)
        ws_a.receive_json()  # roster.updated initial, vide
        _skip_split_mode_snapshot(ws_a)
        ws_a.send_json({"action": "identity.set", "device_key": "device-a", "name": "Sami"})
        ws_a.receive_json()  # écho

        with _connect(client, restaurant, table) as ws_b:
            _skip_cart_snapshot(ws_b)
            assert ws_b.receive_json() == {
                "event": "roster.updated", "people": [{"key": "device-a", "name": "Sami"}],
            }


def test_une_deconnexion_meme_longue_ne_purge_plus_le_roster(client):
    """
    2026-09-09 (demande de Wassim) : même règle que le panier partagé
    (`test_table_cart.py`) — le roster ne doit plus jamais être vidé par une
    déconnexion, aussi longue soit-elle. Seul le bouton « Libérer la table »
    du serveur/manager (`release_table`) le vide désormais. Ici, plus aucun
    appareil n'est connecté à la table après le `with` : si une purge
    automatique existait encore, elle aurait cette fenêtre pour s'exécuter.
    """
    restaurant, table = _setup_restaurant_with_table(client, "roster-clear")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_snapshot(ws)
        ws.receive_json()
        _skip_split_mode_snapshot(ws)
        ws.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        ws.receive_json()

    with _connect(client, restaurant, table) as ws_after:
        _skip_cart_snapshot(ws_after)
        snapshot = ws_after.receive_json()
        assert snapshot == {"event": "roster.updated", "people": [{"key": "device-a", "name": "Ahmed"}]}


def test_rosters_isoles_entre_deux_tables(client):
    restaurant, table_a = _setup_restaurant_with_table(client, "roster-iso-a")
    headers = auth_headers(create_staff(restaurant.id))
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 2"}, headers=headers
    ).json()

    with _connect(client, restaurant, table_a) as ws_a, _connect(client, restaurant, table_b) as ws_b:
        _skip_cart_snapshot(ws_a)
        _skip_cart_snapshot(ws_b)
        ws_a.receive_json()
        ws_b.receive_json()
        _skip_split_mode_snapshot(ws_a)
        _skip_split_mode_snapshot(ws_b)

        ws_a.send_json({"action": "identity.set", "device_key": "device-a", "name": "Ahmed"})
        ws_a.receive_json()

        # Table B n'a rien vu passer de la déclaration de A.
        ws_b.send_json({"action": "identity.set", "device_key": "device-x", "name": "Sami"})
        assert ws_b.receive_json() == {
            "event": "roster.updated", "people": [{"key": "device-x", "name": "Sami"}],
        }
