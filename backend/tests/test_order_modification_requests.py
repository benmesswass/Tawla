"""
Fenêtre 2 : une fois la commande confirmée, le client ne modifie plus
directement (voir test_order_modification.py pour la fenêtre 1) — il envoie
une demande que le serveur accepte ou refuse ligne par ligne, après
vérification avec la cuisine.
"""
from app.modules.orders.models import Order, OrderItem
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup(client):
    restaurant = create_restaurant(name="Café Test")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 5"}, headers=headers
    ).json()
    couscous = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous royal", "price": 24.0},
        headers=headers,
    ).json()
    the = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Thé à la menthe", "price": 3.0},
        headers=headers,
    ).json()
    baklawa = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Baklawa", "price": 4.0},
        headers=headers,
    ).json()
    return restaurant, table, headers, couscous, the, baklawa


def _confirmed_order(client, table, headers, couscous, the):
    """Commande confirmée ET envoyée en cuisine, comme le vrai bouton unique
    "Confirmer" côté staff (confirmAndSend) : 2x Couscous, 3x Thé."""
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [
                {"menu_item_id": couscous["id"], "quantity": 2},
                {"menu_item_id": the["id"], "quantity": 3},
            ],
        },
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers)
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=headers)
    return order


def test_cannot_request_modification_before_confirmation(client):
    """Fenêtre 1 (édition directe) est le bon outil tant que la commande
    attend confirmation — la demande n'a de sens qu'une fois confirmée."""
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": couscous["id"], "quantity": 1}]},
    ).json()

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": the["id"], "quantity": 1}]},
        headers=order_headers(order),
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "MODIFICATION_REQUEST_NOT_ALLOWED"


def test_create_request_builds_one_line_per_changed_item(client):
    """Scénario du mockup : Thé réduit de 3 à 2, Baklawa ajouté à 1. Couscous
    inchangé ne doit produire aucune ligne."""
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={
            "items": [
                {"menu_item_id": couscous["id"], "quantity": 2},
                {"menu_item_id": the["id"], "quantity": 2},
                {"menu_item_id": baklawa["id"], "quantity": 1},
            ]
        },
        headers=order_headers(order),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    lines = {l["menu_item_name"]: l for l in body["lines"]}
    assert set(lines) == {"Thé à la menthe", "Baklawa"}
    assert lines["Thé à la menthe"]["previous_quantity"] == 3
    assert lines["Thé à la menthe"]["requested_quantity"] == 2
    assert lines["Baklawa"]["previous_quantity"] == 0
    assert lines["Baklawa"]["requested_quantity"] == 1
    assert all(l["status"] == "pending" for l in body["lines"])


def test_create_request_rejects_no_actual_change(client):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={
            "items": [
                {"menu_item_id": couscous["id"], "quantity": 2},
                {"menu_item_id": the["id"], "quantity": 3},
            ]
        },
        headers=order_headers(order),
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "NO_CHANGES_REQUESTED"


def test_only_one_pending_request_at_a_time(client):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": baklawa["id"], "quantity": 1}, {"menu_item_id": the["id"], "quantity": 3}]},
        headers=order_headers(order),
    )

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": baklawa["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 3}]},
        headers=order_headers(order),
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "MODIFICATION_REQUEST_ALREADY_PENDING"


def test_order_out_exposes_pending_modification_request(client):
    """Un rafraîchissement de page doit retrouver l'état "en attente" sans
    dépendre uniquement du WebSocket."""
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": baklawa["id"], "quantity": 1}, {"menu_item_id": the["id"], "quantity": 3}]},
        headers=order_headers(order),
    )

    refreshed = client.get(f"/api/v1/orders/{order['id']}", headers=order_headers(order)).json()
    assert refreshed["pending_modification_request"] is not None
    assert refreshed["pending_modification_request"]["status"] == "pending"


def test_staff_resolves_request_partially_accept_and_decline(client, db_session):
    """Le coeur du sujet : le serveur accepte le retrait du thé mais refuse
    l'ajout du Baklawa (cuisine ne peut plus prendre de dessert) — seule la
    ligne acceptée doit se répercuter sur la vraie commande."""
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    request = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 2}, {"menu_item_id": baklawa["id"], "quantity": 1}]},
        headers=order_headers(order),
    ).json()
    lines = {l["menu_item_name"]: l["id"] for l in request["lines"]}

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json={
            "decisions": [
                {"line_id": lines["Thé à la menthe"], "accepted": True},
                {"line_id": lines["Baklawa"], "accepted": False},
            ]
        },
        headers=headers,
    )
    assert res.status_code == 200
    resolved = res.json()
    assert resolved["status"] == "resolved"
    outcomes = {l["menu_item_name"]: l["status"] for l in resolved["lines"]}
    assert outcomes == {"Thé à la menthe": "accepted", "Baklawa": "declined"}

    stored_items = db_session.query(OrderItem).filter(OrderItem.order_id == order["id"]).all()
    quantities = {i.menu_item_name: i.quantity for i in stored_items}
    assert quantities == {"Couscous royal": 2, "Thé à la menthe": 2}  # Baklawa jamais ajouté

    stored_order = db_session.get(Order, order["id"])
    assert stored_order.items_updated_at is not None
    assert stored_order.pending_modification_request is None


def test_resolve_rejects_incomplete_decisions(client):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    request = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 2}, {"menu_item_id": baklawa["id"], "quantity": 1}]},
        headers=order_headers(order),
    ).json()
    only_one_line = request["lines"][0]["id"]

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json={"decisions": [{"line_id": only_one_line, "accepted": True}]},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "INCOMPLETE_RESOLUTION"


def test_cannot_resolve_already_resolved_request(client):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    request = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 3}, {"menu_item_id": baklawa["id"], "quantity": 1}]},
        headers=order_headers(order),
    ).json()
    line_id = request["lines"][0]["id"]
    decisions = {"decisions": [{"line_id": line_id, "accepted": True}]}
    client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json=decisions, headers=headers,
    )

    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json=decisions, headers=headers,
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "MODIFICATION_REQUEST_ALREADY_RESOLVED"


def test_fully_accepted_new_item_is_added_to_the_order(client, db_session):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    request = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 3}, {"menu_item_id": baklawa["id"], "quantity": 2}]},
        headers=order_headers(order),
    ).json()
    line_id = request["lines"][0]["id"]

    client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json={"decisions": [{"line_id": line_id, "accepted": True}]},
        headers=headers,
    )

    stored_items = db_session.query(OrderItem).filter(OrderItem.order_id == order["id"]).all()
    baklawa_line = next(i for i in stored_items if i.menu_item_name == "Baklawa")
    assert baklawa_line.quantity == 2
    assert float(baklawa_line.unit_price) == 4.0


def test_fully_accepted_full_removal_deletes_the_item(client, db_session):
    """requested_quantity=0 accepté doit vraiment supprimer la ligne, pas la
    laisser à zéro."""
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    request = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}]},  # Thé retiré entièrement
        headers=order_headers(order),
    ).json()
    line_id = request["lines"][0]["id"]

    client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json={"decisions": [{"line_id": line_id, "accepted": True}]},
        headers=headers,
    )

    stored_items = db_session.query(OrderItem).filter(OrderItem.order_id == order["id"]).all()
    assert [i.menu_item_name for i in stored_items] == ["Couscous royal"]


def test_resolve_isolated_per_restaurant(client):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    request = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 2}]},
        headers=order_headers(order),
    ).json()

    _other_restaurant, _other_table, other_headers, *_ = _setup(client)
    res = client.post(
        f"/api/v1/orders/{order['id']}/modification-requests/{request['id']}/resolve",
        json={"decisions": [{"line_id": request["lines"][0]["id"], "accepted": True}]},
        headers=other_headers,
    )
    assert res.status_code == 404


def test_list_pending_modification_requests(client):
    restaurant, table, headers, couscous, the, baklawa = _setup(client)
    order = _confirmed_order(client, table, headers, couscous, the)
    client.post(
        f"/api/v1/orders/{order['id']}/modification-requests",
        json={"items": [{"menu_item_id": couscous["id"], "quantity": 2}, {"menu_item_id": the["id"], "quantity": 2}]},
        headers=order_headers(order),
    )

    res = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-modification-requests", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["table_label"] == "Table 5"
    assert body[0]["order_id"] == order["id"]
