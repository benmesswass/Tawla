"""
Paiement carte du client connecté à Konnect — modèle DIRECT (2026-08-19) :
réglé chez le restaurant, jamais chez Tawla (dont le wallet ne sert qu'à son
propre abonnement, voir test_subscription_payments.py). `test_demo_*` couvrent
le mode démonstration, exercé par tout restaurant n'ayant rien connecté.
`test_konnect_*` couvrent le chemin réel, dormant tant que ce restaurant
précis n'a pas sa propre clé — Konnect lui-même est simulé via monkeypatch,
jamais un vrai appel réseau.
"""
from app.core.crypto import encrypt_field
from app.core.konnect import KonnectError, KonnectPayment
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order, PaymentMethod, PaymentStatus
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant, SubscriptionTier
from tests.conftest import _TestingSessionLocal, auth_headers, create_restaurant, create_staff, order_headers


def _manager_headers(restaurant_id: int) -> dict[str, str]:
    return auth_headers(create_staff(restaurant_id, StaffRole.MANAGER))


def _connect_konnect(restaurant: Restaurant, *, api_key: str = "konnect-test-key", wallet_id: str = "wallet-abc") -> None:
    db = _TestingSessionLocal()
    r = db.get(Restaurant, restaurant.id)
    r.konnect_api_key_encrypted = encrypt_field(api_key)
    r.konnect_wallet_id = wallet_id
    db.commit()
    db.close()


def _setup_order(client, restaurant: Restaurant, *, price: float = 20, quantity: int = 2) -> dict:
    manager_headers = _manager_headers(restaurant.id)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": price},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": quantity}]},
    ).json()
    confirmed = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers).json()
    return {**order, **confirmed}


# --- Mode démonstration (restaurant n'ayant rien connecté) ------------------


def test_demo_card_payment_pays_immediately_without_konnect_credentials(client):
    restaurant = create_restaurant(slug="card-demo-no-credentials")
    order = _setup_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 200
    body = res.json()
    assert body["payment_status"] == "paid"
    assert body.get("pay_url") is None


def test_demo_card_payment_used_even_with_credentials_if_payment_mode_not_konnect(client):
    """Anti-activation accidentelle : la clé seule ne suffit pas, il faut
    aussi PAYMENT_MODE=konnect (même garde-fou que l'abonnement)."""
    restaurant = create_restaurant(slug="card-demo-mode-off")
    _connect_konnect(restaurant)
    order = _setup_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"


# --- Chemin Konnect réel (dormant, simulé via monkeypatch) ------------------


def test_konnect_card_payment_stays_pending_and_uses_the_restaurants_own_wallet(client, db_session, monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    restaurant = create_restaurant(slug="card-konnect-init")
    _connect_konnect(restaurant, api_key="resto-key", wallet_id="resto-wallet")
    order = _setup_order(client, restaurant, price=20, quantity=2)

    captured = {}

    def _fake_init(**kwargs):
        captured.update(kwargs)
        return "https://pay.konnect.example/x", "ref-123"

    monkeypatch.setattr(orders_service, "init_konnect_payment", _fake_init)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 5}, headers=order_headers(order))

    assert res.status_code == 200
    body = res.json()
    assert body["pay_url"] == "https://pay.konnect.example/x"
    assert body["payment_status"] == "pending"  # jamais payé tant que Konnect n'a pas confirmé

    # Le wallet et la clé utilisés sont ceux du RESTAURANT, pas ceux
    # (inexistants ici) de Tawla — c'est tout l'enjeu du modèle direct.
    assert captured["api_key"] == "resto-key"
    assert captured["receiver_wallet_id"] == "resto-wallet"
    assert captured["amount_tnd"] == 45  # 2 x 20 DT + 5 DT de pourboire

    db_order = db_session.get(Order, order["id"])
    assert db_order.payment_method == PaymentMethod.CARD
    assert db_order.payment_status == PaymentStatus.PENDING
    assert db_order.payment_ref == "ref-123"


def test_konnect_card_payment_init_failure_returns_502(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    restaurant = create_restaurant(slug="card-konnect-init-fails")
    _connect_konnect(restaurant)
    order = _setup_order(client, restaurant)

    def _boom(**kwargs):
        raise KonnectError("réseau indisponible")

    monkeypatch.setattr(orders_service, "init_konnect_payment", _boom)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 502
    assert res.json()["detail"]["code"] == "PAYMENT_INIT_FAILED"


def test_konnect_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    restaurant = create_restaurant(slug="card-webhook-bad-sig")
    order = _setup_order(client, restaurant)

    res = client.get(f"/api/v1/orders/{order['id']}/pay/card/webhook", params={"sig": "not-the-real-one"})

    assert res.status_code == 401


def test_konnect_webhook_disabled_when_payment_mode_is_not_konnect(client):
    restaurant = create_restaurant(slug="card-webhook-disabled")
    order = _setup_order(client, restaurant)

    res = client.get(f"/api/v1/orders/{order['id']}/pay/card/webhook", params={"sig": "whatever"})

    assert res.status_code == 404


def _pending_konnect_order(client, restaurant: Restaurant, *, price: float = 20, quantity: int = 1) -> dict:
    _connect_konnect(restaurant)
    order = _setup_order(client, restaurant, price=price, quantity=quantity)
    db = _TestingSessionLocal()
    db_order = db.get(Order, order["id"])
    db_order.payment_method = PaymentMethod.CARD
    db_order.payment_status = PaymentStatus.PENDING
    db_order.payment_ref = "ref-abc"
    db.commit()
    db.close()
    return order


def test_settle_applies_paid_and_clears_the_pending_state(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="card-settle-completed")
    order = _pending_konnect_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_konnect_payment",
        lambda ref, api_key=None: KonnectPayment(id=ref, status="completed", amount=20_000, reached_amount=20_000),
    )

    import asyncio

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "paid"
    db_order = db_session.get(Order, order["id"])
    db_session.refresh(db_order)
    assert db_order.payment_status == PaymentStatus.PAID


def test_settle_is_a_noop_when_payment_still_pending(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="card-settle-pending")
    order = _pending_konnect_order(client, restaurant)
    monkeypatch.setattr(
        orders_service, "get_konnect_payment",
        lambda ref, api_key=None: KonnectPayment(id=ref, status="pending", amount=20_000, reached_amount=0),
    )

    import asyncio

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "pending"
    db_order = db_session.get(Order, order["id"])
    assert db_order.payment_status == PaymentStatus.PENDING


def test_settle_rejects_an_amount_lower_than_the_order_total(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="card-settle-amount-mismatch")
    order = _pending_konnect_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_konnect_payment",
        lambda ref, api_key=None: KonnectPayment(id=ref, status="completed", amount=20_000, reached_amount=1_000),
    )

    import asyncio

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "error"
    db_order = db_session.get(Order, order["id"])
    assert db_order.payment_status == PaymentStatus.PENDING  # rien consommé, un vrai règlement pourra suivre


def test_settle_is_idempotent_against_a_concurrent_replay(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="card-settle-idempotent")
    order = _pending_konnect_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_konnect_payment",
        lambda ref, api_key=None: KonnectPayment(id=ref, status="completed", amount=20_000, reached_amount=20_000),
    )

    import asyncio

    first = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))
    second = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))  # webhook rejoué / course avec /check

    assert first == "paid"
    assert second == "pending"  # plus rien en attente (payment_status n'est plus PENDING)


def test_settle_returns_error_on_konnect_fetch_failure(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="card-settle-fetch-error")
    order = _pending_konnect_order(client, restaurant)

    def _boom(ref, api_key=None):
        raise KonnectError("réseau indisponible")

    monkeypatch.setattr(orders_service, "get_konnect_payment", _boom)

    import asyncio

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "error"


def test_check_endpoint_settles_a_completed_pending_payment(client, monkeypatch):
    restaurant = create_restaurant(slug="card-check-endpoint-settles")
    order = _pending_konnect_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_konnect_payment",
        lambda ref, api_key=None: KonnectPayment(id=ref, status="completed", amount=20_000, reached_amount=20_000),
    )

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card/check", headers=order_headers(order))

    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"


def test_check_endpoint_requires_the_order_token(client):
    restaurant = create_restaurant(slug="card-check-endpoint-no-token")
    order = _pending_konnect_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card/check")

    assert res.status_code == 404  # même contrat que get_order_by_token : jamais 401/403


# --- Connexion du wallet (manager) ------------------------------------------


def test_manager_can_connect_and_replace_konnect_credentials(client):
    restaurant = create_restaurant(slug="card-connect-credentials")
    headers = _manager_headers(restaurant.id)

    res = client.put(
        f"/api/v1/restaurants/{restaurant.id}/konnect-credentials",
        json={"api_key": "sk-live-xyz", "wallet_id": "wallet-123"},
        headers=headers,
    )

    assert res.status_code == 200
    body = res.json()
    assert body["konnect_configured"] is True
    assert body["konnect_wallet_id"] == "wallet-123"
    # Jamais la clé elle-même, sous aucune forme.
    assert "sk-live-xyz" not in res.text
    assert "api_key" not in body

    db = _TestingSessionLocal()
    db_restaurant = db.get(Restaurant, restaurant.id)
    credentials = db_restaurant.konnect_credentials()
    db.close()
    assert credentials == ("sk-live-xyz", "wallet-123")


def test_someone_elses_manager_cannot_connect_konnect_credentials(client):
    restaurant = create_restaurant(slug="card-connect-forbidden")
    other_restaurant = create_restaurant(slug="card-connect-other")
    headers = _manager_headers(other_restaurant.id)

    res = client.put(
        f"/api/v1/restaurants/{restaurant.id}/konnect-credentials",
        json={"api_key": "sk-live-xyz", "wallet_id": "wallet-123"},
        headers=headers,
    )

    assert res.status_code == 403


def test_restaurant_without_credentials_reports_not_configured(client):
    restaurant = create_restaurant(slug="card-not-configured")
    headers = _manager_headers(restaurant.id)

    res = client.get(f"/api/v1/restaurants/{restaurant.id}", headers=headers)

    assert res.json()["konnect_configured"] is False
    assert res.json()["konnect_wallet_id"] is None
