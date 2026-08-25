"""
Paiement carte du client connecté à Stripe — marché `fr` uniquement, miroir de
test_order_card_konnect_payment.py pour core/stripe_provider.py
(MARCHE_FRANCE.md C2/S1-S2). `test_demo_*` couvrent le mode démonstration,
exercé par tout restaurant n'ayant rien connecté. `test_stripe_*` couvrent le
chemin réel, dormant tant que ce restaurant précis n'a pas son propre compte
— Stripe lui-même est simulé via monkeypatch, jamais un vrai appel réseau.

Câblé et testable dès aujourd'hui, jamais activé en production : aucun
compte Stripe n'existe encore pour Tawla, et le bouton client reste grisé
pour le marché France indépendamment de PAYMENT_MODE (voir
frontend/lib/market.ts::onlinePaymentAvailable) — l'arbitrage S1/S2 reste
entier.
"""
import asyncio

from app.core.config import settings
from app.core.stripe_provider import StripeError, StripePayment
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order, PaymentMethod, PaymentStatus
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant
from tests.conftest import _TestingSessionLocal, auth_headers, create_restaurant, create_staff, order_headers


def _manager_headers(restaurant_id: int) -> dict[str, str]:
    return auth_headers(create_staff(restaurant_id, StaffRole.MANAGER))


def _connect_stripe(restaurant: Restaurant, *, account_id: str = "acct_test123") -> None:
    db = _TestingSessionLocal()
    r = db.get(Restaurant, restaurant.id)
    r.stripe_account_id = account_id
    db.commit()
    db.close()


def _setup_order(client, restaurant: Restaurant, *, price: float = 20, quantity: int = 1) -> dict:
    manager_headers = _manager_headers(restaurant.id)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Salade César", "price": price},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": quantity}]},
    ).json()
    confirmed = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers).json()
    return {**order, **confirmed}


def _fr_market(monkeypatch):
    monkeypatch.setattr(settings, "market", "fr")


# --- Mode démonstration (restaurant n'ayant rien connecté) ------------------


def test_demo_card_payment_pays_immediately_in_france_without_stripe_account(client, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-fr-demo-no-account")
    order = _setup_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 200
    body = res.json()
    assert body["payment_status"] == "paid"
    assert body.get("pay_url") is None


def test_demo_card_payment_used_even_with_account_if_payment_mode_not_stripe(client, monkeypatch):
    """Anti-activation accidentelle : le compte connecté seul ne suffit pas,
    il faut aussi PAYMENT_MODE=stripe (même garde-fou que Konnect)."""
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-fr-demo-mode-off")
    _connect_stripe(restaurant)
    order = _setup_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"


def test_tunisia_market_never_uses_stripe_even_with_an_account_connected(client, monkeypatch):
    """La Tunisie ne doit JAMAIS passer par Stripe, même si un compte est
    connecté (n'arrivera pas en pratique — pas d'UI pour ça côté marché tn —
    mais le garde-fou de marché doit tenir tout seul)."""
    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    restaurant = create_restaurant(slug="card-tn-ignores-stripe")
    _connect_stripe(restaurant)
    order = _setup_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"  # mode démo Konnect, jamais Stripe


# --- Chemin Stripe réel (dormant, simulé via monkeypatch) -------------------


def test_stripe_card_payment_stays_pending_and_uses_the_restaurants_own_account(
    client, db_session, monkeypatch
):
    _fr_market(monkeypatch)
    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    restaurant = create_restaurant(slug="card-stripe-init")
    _connect_stripe(restaurant, account_id="acct_resto")
    order = _setup_order(client, restaurant, price=20, quantity=2)

    captured = {}

    def _fake_init(**kwargs):
        captured.update(kwargs)
        return "https://checkout.stripe.example/x", "cs_test_123"

    monkeypatch.setattr(orders_service, "init_stripe_payment", _fake_init)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 5}, headers=order_headers(order))

    assert res.status_code == 200
    body = res.json()
    assert body["pay_url"] == "https://checkout.stripe.example/x"
    assert body["payment_status"] == "pending"  # jamais payé tant que Stripe n'a pas confirmé

    # Le compte utilisé est celui du RESTAURANT — modèle direct charge,
    # jamais celui de Tawla.
    assert captured["connected_account_id"] == "acct_resto"
    assert captured["amount_eur"] == 45  # 2 x 20 € + 5 € de pourboire

    db_order = db_session.get(Order, order["id"])
    assert db_order.payment_method == PaymentMethod.CARD
    assert db_order.payment_status == PaymentStatus.PENDING
    assert db_order.payment_ref == "cs_test_123"


def test_stripe_card_payment_init_failure_returns_502(client, monkeypatch):
    _fr_market(monkeypatch)
    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    restaurant = create_restaurant(slug="card-stripe-init-fails")
    _connect_stripe(restaurant)
    order = _setup_order(client, restaurant)

    def _boom(**kwargs):
        raise StripeError("réseau indisponible")

    monkeypatch.setattr(orders_service, "init_stripe_payment", _boom)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert res.status_code == 502
    assert res.json()["detail"]["code"] == "PAYMENT_INIT_FAILED"


def test_stripe_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    restaurant = create_restaurant(slug="card-stripe-webhook-bad-sig")
    order = _setup_order(client, restaurant)

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card/webhook/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=not-the-real-one"},
    )

    assert res.status_code == 401


def test_stripe_webhook_disabled_when_payment_mode_is_not_stripe(client):
    restaurant = create_restaurant(slug="card-stripe-webhook-disabled")
    order = _setup_order(client, restaurant)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card/webhook/stripe", content=b"{}")

    assert res.status_code == 404


def test_stripe_webhook_accepts_a_valid_signature_and_settles_the_payment(client, monkeypatch):
    """Contrairement au test ci-dessus (signature falsifiée rejetée), calcule
    une VRAIE signature Stripe pour vérifier que le chemin heureux marche
    aussi — sans ce test, on ne prouve que le rejet, jamais l'acceptation."""
    import hmac
    import time
    from hashlib import sha256

    _fr_market(monkeypatch)
    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    restaurant = create_restaurant(slug="card-stripe-webhook-valid-sig")
    order = _pending_stripe_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_stripe_payment",
        lambda ref, account_id: StripePayment(id=ref, status="paid", amount=2000, reached_amount=2000),
    )

    body = b'{"id": "evt_test"}'
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.".encode("utf-8") + body
    signature = hmac.new(b"whsec_test_secret", signed_payload, sha256).hexdigest()

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card/webhook/stripe",
        content=body,
        headers={"stripe-signature": f"t={timestamp},v1={signature}"},
    )

    assert res.status_code == 200
    assert res.json()["result"] == "paid"


def _pending_stripe_order(client, restaurant: Restaurant, *, price: float = 20, quantity: int = 1) -> dict:
    _connect_stripe(restaurant)
    order = _setup_order(client, restaurant, price=price, quantity=quantity)
    db = _TestingSessionLocal()
    db_order = db.get(Order, order["id"])
    db_order.payment_method = PaymentMethod.CARD
    db_order.payment_status = PaymentStatus.PENDING
    db_order.payment_ref = "cs_test_abc"
    db.commit()
    db.close()
    return order


def test_settle_applies_paid_and_clears_the_pending_state(client, db_session, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-settle-completed")
    order = _pending_stripe_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_stripe_payment",
        lambda ref, account_id: StripePayment(id=ref, status="paid", amount=2000, reached_amount=2000),
    )

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "paid"
    db_order = db_session.get(Order, order["id"])
    db_session.refresh(db_order)
    assert db_order.payment_status == PaymentStatus.PAID


def test_settle_is_a_noop_when_payment_still_unpaid(client, db_session, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-settle-pending")
    order = _pending_stripe_order(client, restaurant)
    monkeypatch.setattr(
        orders_service, "get_stripe_payment",
        lambda ref, account_id: StripePayment(id=ref, status="unpaid", amount=2000, reached_amount=0),
    )

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "pending"
    db_order = db_session.get(Order, order["id"])
    assert db_order.payment_status == PaymentStatus.PENDING


def test_settle_rejects_an_amount_lower_than_the_order_total(client, db_session, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-settle-amount-mismatch")
    order = _pending_stripe_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_stripe_payment",
        lambda ref, account_id: StripePayment(id=ref, status="paid", amount=2000, reached_amount=100),
    )

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "error"
    db_order = db_session.get(Order, order["id"])
    assert db_order.payment_status == PaymentStatus.PENDING  # rien consommé, un vrai règlement pourra suivre


def test_settle_is_idempotent_against_a_concurrent_replay(client, db_session, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-settle-idempotent")
    order = _pending_stripe_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_stripe_payment",
        lambda ref, account_id: StripePayment(id=ref, status="paid", amount=2000, reached_amount=2000),
    )

    first = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))
    second = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))  # webhook rejoué

    assert first == "paid"
    assert second == "pending"  # plus rien en attente


def test_settle_returns_error_on_stripe_fetch_failure(client, db_session, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-settle-fetch-error")
    order = _pending_stripe_order(client, restaurant)

    def _boom(ref, account_id):
        raise StripeError("réseau indisponible")

    monkeypatch.setattr(orders_service, "get_stripe_payment", _boom)

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "error"


def test_settle_returns_error_when_stripe_account_disconnected_meanwhile(client, db_session, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-settle-disconnected")
    order = _setup_order(client, restaurant, price=20, quantity=1)  # jamais connecté
    db = _TestingSessionLocal()
    db_order = db.get(Order, order["id"])
    db_order.payment_method = PaymentMethod.CARD
    db_order.payment_status = PaymentStatus.PENDING
    db_order.payment_ref = "cs_test_orphan"
    db.commit()
    db.close()

    result = asyncio.run(orders_service.settle_card_payment(db_session, order["id"]))

    assert result == "error"


def test_check_endpoint_settles_a_completed_pending_payment(client, monkeypatch):
    _fr_market(monkeypatch)
    restaurant = create_restaurant(slug="card-stripe-check-endpoint")
    order = _pending_stripe_order(client, restaurant, price=20, quantity=1)
    monkeypatch.setattr(
        orders_service, "get_stripe_payment",
        lambda ref, account_id: StripePayment(id=ref, status="paid", amount=2000, reached_amount=2000),
    )

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card/check", headers=order_headers(order))

    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"


# --- Connexion du compte (manager) ------------------------------------------


def test_manager_can_connect_and_replace_stripe_account(client):
    restaurant = create_restaurant(slug="card-stripe-connect-account")
    headers = _manager_headers(restaurant.id)

    res = client.put(
        f"/api/v1/restaurants/{restaurant.id}/stripe-account",
        json={"account_id": "acct_new123"},
        headers=headers,
    )

    assert res.status_code == 200
    body = res.json()
    assert body["stripe_configured"] is True
    assert body["stripe_account_id"] == "acct_new123"

    db = _TestingSessionLocal()
    db_restaurant = db.get(Restaurant, restaurant.id)
    db.close()
    assert db_restaurant.stripe_account_id == "acct_new123"


def test_someone_elses_manager_cannot_connect_stripe_account(client):
    restaurant = create_restaurant(slug="card-stripe-connect-forbidden")
    other_restaurant = create_restaurant(slug="card-stripe-connect-other")
    headers = _manager_headers(other_restaurant.id)

    res = client.put(
        f"/api/v1/restaurants/{restaurant.id}/stripe-account",
        json={"account_id": "acct_new123"},
        headers=headers,
    )

    assert res.status_code == 403


def test_restaurant_without_stripe_account_reports_not_configured(client):
    restaurant = create_restaurant(slug="card-stripe-not-configured")
    headers = _manager_headers(restaurant.id)

    res = client.get(f"/api/v1/restaurants/{restaurant.id}", headers=headers)

    assert res.json()["stripe_configured"] is False
