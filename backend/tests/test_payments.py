from datetime import timedelta

from app.core.dates import service_day_start
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order
from app.modules.staff.models import StaffRole
from tests.conftest import _TestingSessionLocal, auth_headers, create_restaurant, create_staff, order_headers


def _setup_order(client, confirmed=True):
    restaurant = create_restaurant(name="Café Paiement", slug="cafe-paiement")
    manager_headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 20},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 2}],
        },
    ).json()
    # Payer une commande non confirmée est refusé depuis le correctif F-5 :
    # la quasi-totalité de ces tests veut une commande payable, donc
    # confirmée par défaut. `confirmed=False` pour les deux qui testent
    # justement ce garde-fou. Fusion (pas remplacement) : la réponse de
    # /confirm est un OrderOutStaff, qui n'a pas `public_token` — un simple
    # remplacement le ferait disparaître pour le reste du test.
    if confirmed:
        confirmed_order = client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers).json()
        order = {**order, **confirmed_order}
    return restaurant, manager_headers, order


def test_pay_by_card_covers_full_amount_plus_tip(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 5}, headers=order_headers(order))
    assert res.status_code == 200
    body = res.json()
    assert body["payment_method"] == "card"
    assert body["payment_status"] == "paid"
    assert body["tip_amount"] == 5
    assert body["total_amount"] == 40  # 2 x 20 DT, hors pourboire


def test_pay_by_card_defaults_to_no_tip(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={}, headers=order_headers(order))
    assert res.status_code == 200
    assert res.json()["tip_amount"] == 0


def test_pay_by_card_rejects_negative_tip(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": -5}, headers=order_headers(order))
    assert res.status_code == 422


def test_cannot_pay_twice(client):
    _restaurant, _headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ALREADY_PAID"


def test_request_cash_payment_notifies_staff_and_is_confirmable(client):
    restaurant, manager_headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))
    assert res.status_code == 200
    assert res.json()["payment_status"] == "pending"
    assert res.json()["payment_method"] == "cash"

    pending = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=manager_headers)
    assert [o["id"] for o in pending.json()] == [order["id"]]

    confirmed = client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["payment_status"] == "paid"

    pending_after = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=manager_headers
    )
    assert pending_after.json() == []


def test_pending_cash_payments_excludes_orders_before_service_day(client):
    """
    F-4 : `list_pending_cash_payments` n'était borné par aucune date — une
    demande d'encaissement vieille de plusieurs jours (table oubliée,
    éventuellement réglée entre-temps par un autre moyen) restait affichée
    indéfiniment à l'écran serveur. Même borne que `list_active_orders`
    (Phase 19.5).
    """
    restaurant, manager_headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))

    db = _TestingSessionLocal()
    db_order = db.get(Order, order["id"])
    db_order.created_at = service_day_start() - timedelta(days=2)
    db.commit()
    db.close()

    pending = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=manager_headers
    )
    assert pending.json() == []


def test_cannot_pay_an_order_that_has_not_been_confirmed(client):
    """
    F-5 : rien n'empêchait de payer une commande que personne, côté
    restaurant, n'avait encore confirmée — `request_cash_payment` suppose
    ensuite (commentaire ligne ~500) que `taken_by_staff_id` est
    "garanti non-nul" à ce stade, ce qui n'est vrai que si la commande est
    déjà confirmée (auto-claim à la confirmation). Sans ce garde-fou, cette
    hypothèse était fausse, et la demande de paiement pouvait ne s'afficher
    sur aucun écran.
    """
    restaurant, _manager_headers, order = _setup_order(client, confirmed=False)
    assert order["status"] == "pending_confirmation"

    card = client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    )
    assert card.status_code == 409
    assert card.json()["detail"]["code"] == "ORDER_NOT_CONFIRMED"

    cash = client.post(
        f"/api/v1/orders/{order['id']}/pay/cash", json={"tip_amount": 0}, headers=order_headers(order)
    )
    assert cash.status_code == 409
    assert cash.json()["detail"]["code"] == "ORDER_NOT_CONFIRMED"


def test_cannot_cancel_an_order_that_has_been_paid(client):
    """F-5 : `transition_status` autorisait CONFIRMED/SENT_TO_KITCHEN ->
    CANCELLED sans jamais regarder `payment_status` — une commande déjà
    réglée pouvait être annulée."""
    restaurant, manager_headers, order = _setup_order(client)
    paid = client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    )
    assert paid.json()["payment_status"] == "paid"

    cancel = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=manager_headers)
    assert cancel.status_code == 409
    assert cancel.json()["detail"]["code"] == "ORDER_ALREADY_PAID"


def test_pending_cash_payment_carries_the_dedicated_server_id(client):
    """
    Le frontend n'affiche la demande de paiement qu'au serveur qui a pris en
    charge la table (le manager voit tout) — ça suppose que taken_by_staff_id
    est bien porté par la liste des demandes en attente.
    """
    restaurant, manager_headers, order = _setup_order(client, confirmed=False)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)

    # Claim avant confirmation (seul moment où claim_order l'autorise) : le
    # correctif F-5 refuse de payer une commande non confirmée, donc sami
    # doit aussi confirmer — l'auto-claim de la confirmation ne le
    # réaffecte pas, il est déjà le serveur assigné.
    client.post(f"/api/v1/orders/{order['id']}/claim", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(sami))
    client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))

    pending = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=manager_headers
    )
    assert pending.json()[0]["taken_by_staff_id"] == sami.id


def test_pending_cash_payments_survives_order_being_served(client):
    """
    Le paiement cash arrive souvent après "servie" — l'endpoint dédié ne doit
    pas dépendre de ACTIVE_STATUSES (qui exclut "served").
    """
    restaurant, manager_headers, order = _setup_order(client)
    sami = create_staff(restaurant.id, role=StaffRole.WAITER)
    karim = create_staff(restaurant.id, role=StaffRole.KITCHEN)
    headers = auth_headers(sami)

    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=headers)
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=headers)
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=auth_headers(karim))
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=auth_headers(karim))
    client.post(f"/api/v1/orders/{order['id']}/mark-served", headers=headers)

    client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))

    pending = client.get(f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=manager_headers)
    assert [o["id"] for o in pending.json()] == [order["id"]]


def test_confirm_cash_payment_rejects_when_no_pending_request(client):
    _restaurant, manager_headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "NO_PENDING_CASH_PAYMENT"


def test_cannot_pay_a_cancelled_order(client):
    _restaurant, headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ORDER_CANCELLED"


def test_pending_cash_payments_isolated_across_restaurants(client):
    restaurant_a, manager_headers_a, order_a = _setup_order(client)
    restaurant_b = create_restaurant(name="Café B Paiement", slug="cafe-b-paiement")
    manager_b = create_staff(restaurant_b.id, role=StaffRole.MANAGER)

    client.post(f"/api/v1/orders/{order_a['id']}/pay/cash", headers=order_headers(order_a))

    res = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant_b.id}/pending-cash-payments", headers=auth_headers(manager_b)
    )
    assert res.json() == []


def test_pay_by_card_is_public_no_auth_required(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))
    assert res.status_code == 200


def test_le_pourboire_est_conserve_sur_un_paiement_en_especes(client):
    """
    Le pourboire n'était lu que sur le chemin carte. En espèces, le client le
    saisissait, il était jeté, et le serveur venait encaisser le total sans
    lui — l'écart n'apparaissait qu'au comptage de la caisse.
    """
    _restaurant, _manager_headers, order = _setup_order(client)

    demande = client.post(
        f"/api/v1/orders/{order['id']}/pay/cash",
        json={"tip_amount": 8.0},
        headers=order_headers(order),
    )

    assert demande.status_code == 200
    assert demande.json()["tip_amount"] == 8.0
    assert demande.json()["payment_status"] == "pending"


def test_une_demande_despeces_sans_pourboire_reste_possible(client):
    """Le champ est facultatif : un client qui ne laisse rien doit pouvoir
    demander l'addition comme avant."""
    _restaurant, _manager_headers, order = _setup_order(client)

    demande = client.post(f"/api/v1/orders/{order['id']}/pay/cash", headers=order_headers(order))

    assert demande.status_code == 200
    assert demande.json()["tip_amount"] == 0


def test_les_horodatages_sortent_avec_leur_fuseau(client):
    """
    Sans fuseau explicite, le navigateur lit « 2026-08-16T15:33:28 » comme une
    heure locale : sur un Mac réglé à UTC+1, une commande passée à l'instant
    s'affichait « en attente depuis 1 h 00 », et chaque commande d'un vrai
    service serait passée pour perdue.
    """
    _restaurant, _manager_headers, order = _setup_order(client)

    lue = client.get(f"/api/v1/orders/{order['id']}", headers=order_headers(order)).json()

    assert lue["created_at"].endswith(("Z", "+00:00")), lue["created_at"]


# --- Carte physique (terminal apporté par un serveur) -----------------------
# Même mécanique que les espèces, moyen de paiement distinct (2026-08-19).


def test_request_card_terminal_payment_notifies_staff_and_is_confirmable(client):
    restaurant, manager_headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card-terminal", headers=order_headers(order))
    assert res.status_code == 200
    assert res.json()["payment_status"] == "pending"
    assert res.json()["payment_method"] == "card_terminal"

    pending = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-card-terminal-payments", headers=manager_headers
    )
    assert [o["id"] for o in pending.json()] == [order["id"]]

    confirmed = client.post(f"/api/v1/orders/{order['id']}/pay/card-terminal/confirm", headers=manager_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["payment_status"] == "paid"

    pending_after = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-card-terminal-payments", headers=manager_headers
    )
    assert pending_after.json() == []


def test_card_terminal_requests_are_isolated_from_cash_requests(client):
    """Les deux moyens partagent la même mécanique (PENDING) : une demande
    carte physique ne doit jamais apparaître dans la liste espèces, et
    réciproquement — sinon un serveur annoncerait le mauvais montant/moyen."""
    restaurant, manager_headers, order = _setup_order(client)

    client.post(f"/api/v1/orders/{order['id']}/pay/card-terminal", headers=order_headers(order))

    cash_pending = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/pending-cash-payments", headers=manager_headers
    )
    assert cash_pending.json() == []


def test_confirm_card_terminal_payment_rejects_when_no_pending_request(client):
    _restaurant, manager_headers, order = _setup_order(client)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card-terminal/confirm", headers=manager_headers)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "NO_PENDING_CARD_TERMINAL_PAYMENT"


def test_cannot_pay_card_terminal_for_an_order_that_has_not_been_confirmed(client):
    _restaurant, _manager_headers, order = _setup_order(client, confirmed=False)

    res = client.post(f"/api/v1/orders/{order['id']}/pay/card-terminal", headers=order_headers(order))
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "ORDER_NOT_CONFIRMED"


# --- Facture PDF -------------------------------------------------------------


def test_invoice_is_downloadable_once_paid(client):
    _restaurant, _headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    res = client.get(f"/api/v1/orders/{order['id']}/invoice", params={"token": order["public_token"]})

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")


def test_invoice_is_not_available_before_payment(client):
    _restaurant, _headers, order = _setup_order(client)

    res = client.get(f"/api/v1/orders/{order['id']}/invoice", params={"token": order["public_token"]})

    assert res.status_code == 404


def test_invoice_rejects_the_wrong_token(client):
    _restaurant, _headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    res = client.get(f"/api/v1/orders/{order['id']}/invoice", params={"token": "not-the-real-token"})

    assert res.status_code == 404


# --- Confirmation de paiement par email -------------------------------------
# Dégradation gracieuse (comme Konnect) : sans RESEND_API_KEY, aucun envoi
# n'est tenté, jamais une erreur qui bloquerait le paiement.


def test_no_email_sent_when_customer_did_not_leave_an_address(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(orders_service, "send_email_with_attachment", lambda **kwargs: calls.append(kwargs) or True)

    _restaurant, _headers, order = _setup_order(client)
    client.post(f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order))

    assert calls == []


def test_no_email_sent_when_resend_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(orders_service, "send_email_with_attachment", lambda **kwargs: calls.append(kwargs) or True)

    _restaurant, _headers, order = _setup_order(client)
    client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"tip_amount": 0, "customer_email": "client@example.com"},
        headers=order_headers(order),
    )

    assert calls == []


def test_confirmation_email_sent_with_invoice_attached_when_address_left(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(orders_service, "send_email_with_attachment", lambda **kwargs: calls.append(kwargs) or True)

    _restaurant, _headers, order = _setup_order(client)
    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"tip_amount": 0, "customer_email": "client@example.com"},
        headers=order_headers(order),
    )

    assert res.status_code == 200
    assert len(calls) == 1
    assert calls[0]["to"] == "client@example.com"
    assert calls[0]["attachment_bytes"].startswith(b"%PDF")


def test_confirmation_email_sent_on_cash_confirmation_not_on_request(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(orders_service, "send_email_with_attachment", lambda **kwargs: calls.append(kwargs) or True)

    restaurant, manager_headers, order = _setup_order(client)
    client.post(
        f"/api/v1/orders/{order['id']}/pay/cash",
        json={"tip_amount": 0, "customer_email": "client@example.com"},
        headers=order_headers(order),
    )
    assert calls == []  # pas encore payée, juste demandée

    client.post(f"/api/v1/orders/{order['id']}/pay/cash/confirm", headers=manager_headers)
    assert len(calls) == 1


def test_a_failing_pdf_generation_never_breaks_the_payment_itself(client, monkeypatch):
    """Best-effort absolu (voir docstring de _send_payment_confirmation) : un
    nom de plat en arabe, par exemple, ferait échouer le rendu PDF (police du
    cœur latin-1 uniquement) — le paiement, lui, doit rester acquis."""
    monkeypatch.setenv("RESEND_API_KEY", "test-key")

    def _boom(order, restaurant_name):
        raise ValueError("rendu PDF impossible")

    monkeypatch.setattr(orders_service, "generate_invoice_pdf", _boom)

    _restaurant, _headers, order = _setup_order(client)
    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"tip_amount": 0, "customer_email": "client@example.com"},
        headers=order_headers(order),
    )

    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"
