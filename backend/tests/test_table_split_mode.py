"""
Mode de répartition de l'addition (« par plat » / « équitable ») — chantier
hiérarchie du paiement (Wassim, 2026-09-10, ADR 0006). À la différence du
roster (purement déclaratif), CE choix détermine le montant réellement
facturé à chacun : `orders/split.py::compute_payable_amount` le lit au moment
de payer, jamais un affichage à part.
"""

from app.modules.orders import split
from app.modules.orders.models import Order, OrderItem
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup_restaurant_with_table(client, slug):
    restaurant = create_restaurant(name="Dar Chaabane", slug=slug)
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    return restaurant, table, headers


def _connect(client, restaurant, table):
    return client.websocket_connect(f"/ws/table/{restaurant.id}/{table['qr_token']}")


def _skip_cart_and_roster_snapshots(ws):
    ws.receive_json()  # cart.updated
    ws.receive_json()  # roster.updated


# --- Diffusion temps réel (même style que test_table_roster.py) ---------


def test_le_mode_par_defaut_est_par_plat(client):
    restaurant, table, _headers = _setup_restaurant_with_table(client, "split-mode-default")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_and_roster_snapshots(ws)
        assert ws.receive_json() == {"event": "split_mode.updated", "mode": "items"}


def test_choisir_equitable_est_diffuse_a_tous_les_appareils(client):
    restaurant, table, _headers = _setup_restaurant_with_table(client, "split-mode-live")

    with _connect(client, restaurant, table) as ws_a, _connect(client, restaurant, table) as ws_b:
        _skip_cart_and_roster_snapshots(ws_a)
        _skip_cart_and_roster_snapshots(ws_b)
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"action": "split_mode.set", "mode": "equal"})
        expected = {"event": "split_mode.updated", "mode": "equal"}
        assert ws_a.receive_json() == expected
        assert ws_b.receive_json() == expected


def test_un_mode_invalide_est_ignore(client):
    restaurant, table, _headers = _setup_restaurant_with_table(client, "split-mode-invalid")

    with _connect(client, restaurant, table) as ws:
        _skip_cart_and_roster_snapshots(ws)
        ws.receive_json()

        # Un client d'une version différente (ou un message malformé) ne doit
        # ni faire tomber le canal ni corrompre le mode déjà en vigueur — même
        # principe que `identity.set`/`identity.add_guest` : la diffusion qui
        # suit reflète l'état réel (inchangé), jamais la valeur envoyée.
        ws.send_json({"action": "split_mode.set", "mode": "au-plus-riche"})
        assert ws.receive_json() == {"event": "split_mode.updated", "mode": "items"}
        ws.send_json({"action": "split_mode.set", "mode": "equal"})
        assert ws.receive_json() == {"event": "split_mode.updated", "mode": "equal"}


def test_un_appareil_qui_rejoint_voit_le_mode_deja_choisi(client):
    restaurant, table, _headers = _setup_restaurant_with_table(client, "split-mode-join")

    with _connect(client, restaurant, table) as ws_a:
        _skip_cart_and_roster_snapshots(ws_a)
        ws_a.receive_json()
        ws_a.send_json({"action": "split_mode.set", "mode": "equal"})
        ws_a.receive_json()  # écho

        with _connect(client, restaurant, table) as ws_b:
            _skip_cart_and_roster_snapshots(ws_b)
            assert ws_b.receive_json() == {"event": "split_mode.updated", "mode": "equal"}


def test_modes_isoles_entre_deux_tables(client):
    restaurant, table_a, headers = _setup_restaurant_with_table(client, "split-mode-iso-a")
    table_b = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 2"}, headers=headers
    ).json()

    with _connect(client, restaurant, table_a) as ws_a, _connect(client, restaurant, table_b) as ws_b:
        _skip_cart_and_roster_snapshots(ws_a)
        _skip_cart_and_roster_snapshots(ws_b)
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"action": "split_mode.set", "mode": "equal"})
        ws_a.receive_json()

        with _connect(client, restaurant, table_b) as ws_b2:
            _skip_cart_and_roster_snapshots(ws_b2)
            assert ws_b2.receive_json() == {"event": "split_mode.updated", "mode": "items"}


# --- Calcul pur (orders/split.py) ---------------------------------------


def _order_with_items(prices_and_owners: list[tuple[float, str | None]]) -> Order:
    order = Order(restaurant_id=1, table_id=1)
    order.items = [
        OrderItem(menu_item_id=1, menu_item_name="Plat", unit_price=price, quantity=1, added_by_name=owner)
        for price, owner in prices_and_owners
    ]
    return order


def test_mode_equitable_ignore_lattribution_par_plat():
    order = _order_with_items([(30, "Ahmed"), (10, "Sami")])
    shares = split.compute_shares(order, ["Ahmed", "Sami"], mode="equal")
    assert shares == {"Ahmed": 20.0, "Sami": 20.0}


def test_mode_par_plat_reste_le_defaut():
    order = _order_with_items([(30, "Ahmed"), (10, "Sami")])
    assert split.compute_shares(order, ["Ahmed", "Sami"]) == {"Ahmed": 30.0, "Sami": 10.0}


def test_le_dernier_convive_absorbe_larrondi_meme_en_mode_equitable():
    order = _order_with_items([(10, "Ahmed"), (10, "Sami"), (10, "Yassine")])
    amount = split.compute_payable_amount(
        order, ["Ahmed", "Sami", "Yassine"], "Yassine", {"Ahmed", "Sami"}, mode="equal"
    )
    assert amount == order.amount_remaining


# --- Intégration : le mode choisi détermine le montant réellement facturé -


def test_choisir_equitable_change_le_montant_reellement_facture(client):
    """
    Le test qui compte : un mode choisi sur le canal de la table doit changer
    ce qu'on débite réellement, pas seulement un affichage. Ahmed a commandé
    pour 30 DT, Sami pour 10 DT (40 DT au total) — en « par plat » Ahmed doit
    30 DT, en « équitable » 20 DT.
    """
    restaurant, table, headers = _setup_restaurant_with_table(client, "split-mode-charge")
    item_a = client.post(
        "/api/v1/menu-items", json={"restaurant_id": restaurant.id, "name": "Plat cher", "price": 30},
        headers=headers,
    ).json()
    item_b = client.post(
        "/api/v1/menu-items", json={"restaurant_id": restaurant.id, "name": "Plat léger", "price": 10},
        headers=headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [
                {"menu_item_id": item_a["id"], "quantity": 1, "added_by_name": "Ahmed"},
                {"menu_item_id": item_b["id"], "quantity": 1, "added_by_name": "Sami"},
            ],
        },
    ).json()
    order = {**order, **client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers).json()}

    with _connect(client, restaurant, table) as ws:
        _skip_cart_and_roster_snapshots(ws)
        ws.receive_json()
        ws.send_json({"action": "identity.set", "device_key": "device-ahmed", "name": "Ahmed"})
        ws.receive_json()
        ws.send_json({"action": "identity.set", "device_key": "device-sami", "name": "Sami"})
        ws.receive_json()
        ws.send_json({"action": "split_mode.set", "mode": "equal"})
        ws.receive_json()

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"tip_amount": 0, "payer_key": "device-ahmed", "payer_name": "Ahmed"},
        headers=order_headers(order),
    )
    assert res.status_code == 200
    payment = next(p for p in res.json()["payments"] if p["payer_name"] == "Ahmed")
    assert payment["amount"] == 20  # équitable (40 / 2), pas 30 (sa part "par plat")
