"""
Surface publique du parcours client (Phase 12.2).

Un test par constat de la revue d'investissement du 2026-08-13
(`REVUE_INVESTISSEURS.md` § 4). Chacun échoue sur le code d'avant la phase et
passe après.

Le principe posé par cette phase : le parcours client reste **sans compte**
(pas d'inscription pour commander, c'est un choix produit), mais chaque appel
doit être **lié** à quelque chose que seul le vrai client possède — le
`qr_token` de la table qu'il a scannée, ou le `public_token` que la création de
sa commande lui a renvoyé. « Public » ne veut pas dire « non lié ».
"""
from starlette.websockets import WebSocketDisconnect

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.notifications.dependencies import WS_UNAUTHORIZED
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _setup(client, db_session):
    """Un restaurant avec une table et un plat, prêt à recevoir une commande."""
    restaurant = create_restaurant(name="Chez Slah", slug=f"chez-slah-{id(client)}")
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=25.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


def _create_order(client, table, item, loyalty_phone="+21698123456"):
    response = client.post("/api/v1/orders", json={
        "qr_token": table.qr_token,
        "loyalty_phone": loyalty_phone,
        "items": [{"menu_item_id": item.id, "quantity": 2}],
    })
    assert response.status_code == 201, response.text
    return response.json()


def _order_headers(order: dict) -> dict[str, str]:
    return {"X-Order-Token": order["public_token"]}


# --- Constat 1 : lecture d'une commande sans auth, par ID séquentiel ---------


def test_order_cannot_be_read_without_its_token(client, db_session):
    _, table, item = _setup(client, db_session)
    order = _create_order(client, table, item)

    anonymous = client.get(f"/api/v1/orders/{order['id']}")
    assert anonymous.status_code == 404
    assert anonymous.json()["detail"]["code"] == "ORDER_NOT_FOUND"

    with_token = client.get(f"/api/v1/orders/{order['id']}", headers=_order_headers(order))
    assert with_token.status_code == 200
    assert with_token.json()["id"] == order["id"]


def test_order_token_of_another_order_is_refused(client, db_session):
    """Le token doit être lié à SA commande, pas être un sésame global."""
    _, table, item = _setup(client, db_session)
    mine = _create_order(client, table, item)
    other = _create_order(client, table, item, loyalty_phone="+21655000111")

    response = client.get(f"/api/v1/orders/{other['id']}", headers=_order_headers(mine))
    assert response.status_code == 404


def test_sequential_ids_cannot_be_enumerated(client, db_session):
    """Le cœur du constat : deviner 1..N ne donne plus rien."""
    _, table, item = _setup(client, db_session)
    _create_order(client, table, item)

    for order_id in range(1, 6):
        assert client.get(f"/api/v1/orders/{order_id}").status_code == 404


def test_customer_phone_number_never_appears_in_the_public_response(client, db_session):
    """Un numéro de téléphone est une donnée personnelle (loi 2004-63) : il ne
    doit pas sortir sur la réponse que lit le navigateur du client."""
    _, table, item = _setup(client, db_session)
    order = _create_order(client, table, item)

    body = client.get(f"/api/v1/orders/{order['id']}", headers=_order_headers(order)).json()
    assert "loyalty_phone" not in body


def test_staff_still_sees_the_phone_number(client, db_session):
    """Contre-épreuve : le serveur en a besoin pour la fidélité, il le voit."""
    restaurant, table, item = _setup(client, db_session)
    _create_order(client, table, item)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    listed = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(waiter)
    )
    assert listed.status_code == 200
    assert listed.json()[0]["loyalty_phone"] == "+21698123456"


# --- Constat 2 : paiement carte marquable sans auth --------------------------


def test_card_payment_requires_the_order_token(client, db_session):
    restaurant, table, item = _setup(client, db_session)
    order = _create_order(client, table, item)
    # Payer une commande non confirmée est refusé depuis le correctif F-5.
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(create_staff(restaurant.id)))

    anonymous = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0})
    assert anonymous.status_code == 404

    # La commande n'a pas bougé.
    still_unpaid = client.get(f"/api/v1/orders/{order['id']}", headers=_order_headers(order))
    assert still_unpaid.json()["payment_status"] == "unpaid"

    legitimate = client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 2}, headers=_order_headers(order)
    )
    assert legitimate.status_code == 200
    assert legitimate.json()["payment_status"] == "paid"


def test_cash_payment_request_requires_the_order_token(client, db_session):
    restaurant, table, item = _setup(client, db_session)
    order = _create_order(client, table, item)
    # Payer une commande non confirmée est refusé depuis le correctif F-5.
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(create_staff(restaurant.id)))

    assert client.post(f"/api/v1/orders/{order['id']}/pay/cash").status_code == 404
    assert client.post(
        f"/api/v1/orders/{order['id']}/pay/cash", headers=_order_headers(order)
    ).status_code == 200


# --- Constat 3 : commande créée sans avoir scanné le QR ----------------------


def test_order_cannot_be_created_from_a_guessed_table_id(client, db_session):
    """Le pire scénario opérationnel : injecter des commandes dans un service
    en cours en devinant des identifiants numériques."""
    _, table, item = _setup(client, db_session)

    guessed = client.post("/api/v1/orders", json={
        "restaurant_id": table.restaurant_id,
        "table_id": table.id,
        "items": [{"menu_item_id": item.id, "quantity": 50}],
    })
    assert guessed.status_code == 422  # qr_token manquant


def test_order_creation_rejects_an_unknown_qr_token(client, db_session):
    _, _, item = _setup(client, db_session)

    response = client.post("/api/v1/orders", json={
        "qr_token": "token-inexistant",
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    })
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "INVALID_TABLE_CODE"


def test_menu_item_of_another_restaurant_is_refused(client, db_session):
    """Le restaurant est déduit du qr_token : on ne peut plus commander le
    plat du voisin en manipulant restaurant_id."""
    _, table, _ = _setup(client, db_session)
    other = create_restaurant(name="Voisin", slug="voisin-surface")
    foreign_item = MenuItem(restaurant_id=other.id, name="Lablabi", price=8.0, category="Plats")
    db_session.add(foreign_item)
    db_session.commit()
    db_session.refresh(foreign_item)

    response = client.post("/api/v1/orders", json={
        "qr_token": table.qr_token,
        "items": [{"menu_item_id": foreign_item.id, "quantity": 1}],
    })
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ITEM_NOT_FOUND"


# --- Constat 4 : fiche fidélité interrogeable sans auth ----------------------


def test_public_loyalty_lookup_never_exposes_the_birth_date(client, db_session):
    _restaurant, table, item = _setup(client, db_session)
    phone = "+21698123456"
    client.post("/api/v1/orders", json={
        "qr_token": table.qr_token,
        "loyalty_phone": phone,
        "loyalty_birth_date": "1990-05-14",
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    })

    response = client.post(
        "/api/v1/loyalty/lookup", json={"qr_token": table.qr_token, "phone_number": phone}
    )
    assert response.status_code == 200
    assert "birth_date" not in response.json()
    # Le bandeau anniversaire reste calculé côté serveur.
    assert "is_birthday_today" in response.json()


# --- Constat 5 : canal WebSocket staff ouvert --------------------------------


def test_staff_websocket_refuses_a_connection_without_token(client, db_session):
    restaurant, _, _ = _setup(client, db_session)

    with pytest_raises_ws(client, f"/ws/staff/{restaurant.id}"):
        pass


def test_kitchen_websocket_refuses_a_connection_without_token(client, db_session):
    restaurant, _, _ = _setup(client, db_session)

    with pytest_raises_ws(client, f"/ws/kitchen/{restaurant.id}"):
        pass


def test_staff_websocket_refuses_a_token_of_another_restaurant(client, db_session):
    restaurant, _, _ = _setup(client, db_session)
    other = create_restaurant(name="Voisin", slug="voisin-ws")
    intruder = create_staff(other.id, StaffRole.WAITER)
    token = _token_of(intruder)

    with pytest_raises_ws(client, f"/ws/staff/{restaurant.id}?token={token}"):
        pass


def test_staff_websocket_accepts_its_own_staff(client, db_session):
    restaurant, table, item = _setup(client, db_session)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    with client.websocket_connect(f"/ws/staff/{restaurant.id}?token={_token_of(waiter)}") as ws:
        _create_order(client, table, item)
        message = ws.receive_json()
        assert message["event"] == "order.pending_confirmation"
        # Le numéro de téléphone ne transite pas sur le canal d'annonce.
        assert "loyalty_phone" not in message


def test_order_websocket_requires_the_order_token(client, db_session):
    restaurant, table, item = _setup(client, db_session)
    order = _create_order(client, table, item)

    with pytest_raises_ws(client, f"/ws/order/{restaurant.id}/{order['id']}"):
        pass

    with client.websocket_connect(
        f"/ws/order/{restaurant.id}/{order['id']}?token={order['public_token']}"
    ) as ws:
        assert ws is not None


def test_menu_websocket_stays_open_to_everyone(client, db_session):
    """Contre-épreuve : ce canal ne porte que les ruptures de stock, il doit
    rester accessible au client qui lit le menu avant de commander."""
    restaurant, _, _ = _setup(client, db_session)

    with client.websocket_connect(f"/ws/menu/{restaurant.id}") as ws:
        assert ws is not None


# --- Constat 6 : contre-épreuve, l'auth staff reste bien cloisonnée ---------


def test_authenticated_routes_remain_isolated_between_restaurants(client, db_session):
    restaurant, table, item = _setup(client, db_session)
    _create_order(client, table, item)
    other = create_restaurant(name="Voisin", slug="voisin-iso")
    intruder = create_staff(other.id, StaffRole.MANAGER)

    stats = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(intruder))
    assert stats.status_code == 403

    orders = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(intruder)
    )
    assert orders.status_code == 403


# --- Constat 7 : création de restaurant sans auth ---------------------------


def test_anonymous_restaurant_creation_endpoint_is_gone(client):
    response = client.post("/api/v1/restaurants", json={"name": "Squat", "slug": "squat-1"})
    assert response.status_code in (404, 405)


# --- Divers : abonnement push ----------------------------------------------


def test_push_subscription_requires_the_order_token(client, db_session):
    """Sans lien, n'importe qui pouvait remplacer l'abonnement push d'une
    commande et détourner sa notification."""
    _, table, item = _setup(client, db_session)
    order = _create_order(client, table, item)
    payload = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "x", "auth": "y"}}

    assert client.post(f"/api/v1/orders/{order['id']}/push-subscription", json=payload).status_code == 404
    assert client.post(
        f"/api/v1/orders/{order['id']}/push-subscription", json=payload, headers=_order_headers(order)
    ).status_code == 204


# --- Utilitaires ------------------------------------------------------------


def _token_of(staff) -> str:
    from app.modules.staff.security import create_access_token

    return create_access_token(staff.id, staff.restaurant_id, staff.role.value)


class pytest_raises_ws:
    """
    Petit contexte : affirme qu'un canal refuse la connexion avec le code
    applicatif 4401.

    Le serveur accepte la poignée de main puis ferme immédiatement, à dessein :
    un rejet avant `accept()` arriverait au navigateur en code 1006, que le
    frontend ne peut pas distinguer d'une coupure réseau — il réessaierait
    indéfiniment. La socket n'est jamais enregistrée côté serveur, donc aucun
    message ne peut lui parvenir.
    """

    def __init__(self, client, path: str):
        self._client = client
        self._path = path

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        try:
            with self._client.websocket_connect(self._path) as ws:
                # Le TestClient renvoie la trame de fermeture comme un message
                # `websocket.close` ; seuls receive_text/json lèvent.
                message = ws.receive()
        except WebSocketDisconnect as disconnect:
            assert disconnect.code == WS_UNAUTHORIZED, (
                f"{self._path} fermé avec {disconnect.code}, attendu {WS_UNAUTHORIZED}"
            )
            return True
        except Exception:
            # Refus au niveau de la poignée de main : acceptable pour la
            # sécurité, mais indistinguable d'une coupure réseau côté client.
            raise AssertionError(f"{self._path} refusé sans code applicatif 4401")

        assert message["type"] == "websocket.close", (
            f"{self._path} a laissé passer un message : {message}"
        )
        assert message.get("code") == WS_UNAUTHORIZED, (
            f"{self._path} fermé avec {message.get('code')}, attendu {WS_UNAUTHORIZED}"
        )
        return True
