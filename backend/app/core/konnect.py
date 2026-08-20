"""
Client Konnect (passerelle de paiement tunisienne) — abonnement Tawla.

Intégration OPTIONNELLE et à dégradation gracieuse : sans `KONNECT_API_KEY` +
`KONNECT_RECEIVER_WALLET_ID`, le paiement reste en mode démonstration
(règlement immédiat simulé, cf. subscription_payments.py). Dès que ces deux
variables sont définies ET que `PAYMENT_MODE=konnect` est posé explicitement,
le flux réel Konnect prend le relais — la simple présence des clés ne suffit
jamais à elle seule (anti-activation accidentelle, même principe que Darna,
voir src/lib/modes.ts::paymentMode).

Doc : https://docs.konnect.network/docs/en/api-integration/endpoints/initiate-payment
"""
import hmac
import os
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import httpx

KONNECT_API_URL = os.environ.get("KONNECT_API_URL", "https://api.sandbox.konnect.network/api/v2")

# Moyens de paiement proposés sur la passerelle.
_ACCEPTED_PAYMENT_METHODS = ["wallet", "bank_card", "e-DINAR", "flouci"]


def tnd_to_millimes(tnd: float) -> int:
    """Le TND est libellé en millimes par Konnect (1 TND = 1000 millimes)."""
    return round(tnd * 1000)


def is_konnect_enabled() -> bool:
    """
    Vrai si le paiement réel Konnect est ACTIF. Piloté EXPLICITEMENT par
    `PAYMENT_MODE=konnect` — lu à chaque appel (jamais mis en cache), pour
    qu'un changement de variable d'environnement prenne effet sans redéploiement
    du code.
    """
    return os.environ.get("PAYMENT_MODE") == "konnect"


def is_subscription_konnect_enabled() -> bool:
    """
    Vrai si le paiement réel Konnect est utilisable pour l'ABONNEMENT Tawla
    précisément — pas seulement si `PAYMENT_MODE=konnect` est posé.

    `PAYMENT_MODE` est un interrupteur UNIQUE partagé avec le paiement carte
    du client (modèle direct, wallet de CHAQUE restaurant, voir
    `Restaurant.konnect_credentials()`) : l'activer pour l'un active
    mécaniquement `is_konnect_enabled()` pour l'autre. Côté abonnement il n'y
    a pas d'équivalent par-restaurant à vérifier — seulement les variables
    globales `KONNECT_API_KEY`/`KONNECT_RECEIVER_WALLET_ID` (wallet de Tawla
    elle-même). Sans elles, activer Konnect pour le paiement carte ferait
    sortir le checkout d'abonnement du mode démo alors qu'aucune clé réelle
    n'existe pour lui : `init_konnect_payment` lèverait `KonnectError` et le
    checkout renverrait 502 au lieu de rester en démo.
    """
    return (
        is_konnect_enabled()
        and bool(os.environ.get("KONNECT_API_KEY"))
        and bool(os.environ.get("KONNECT_RECEIVER_WALLET_ID"))
    )


def _webhook_key() -> bytes:
    """
    Clé de signature du webhook. Konnect NE signe PAS ses webhooks (simple GET
    `?payment_ref=…`) : on signe donc nous-mêmes l'URL de webhook à l'init, puis
    on revérifie cette signature à la réception (voir sign/verify ci-dessous).
    Clé dédiée `KONNECT_WEBHOOK_SECRET` si fournie, sinon dérivée de
    `JWT_SECRET` (toujours présent) avec séparation de domaine — jamais réutiliser
    un secret tel quel pour un autre usage cryptographique.
    """
    dedicated = os.environ.get("KONNECT_WEBHOOK_SECRET")
    if dedicated:
        return dedicated.encode("utf-8")
    from app.core.config import settings

    return hmac.new(settings.jwt_secret.encode("utf-8"), b"konnect-webhook", sha256).digest()


def sign_konnect_webhook(restaurant_id: int) -> str:
    """Signe l'identifiant du restaurant pour l'URL de webhook (HMAC-SHA256, hex)."""
    return hmac.new(_webhook_key(), str(restaurant_id).encode("utf-8"), sha256).hexdigest()


def verify_konnect_webhook(restaurant_id: int, sig: str) -> bool:
    """Vérifie en temps constant la signature d'un webhook Konnect — rejette
    toute signature absente ou falsifiée (anti-forge)."""
    if not sig:
        return False
    return hmac.compare_digest(sign_konnect_webhook(restaurant_id), sig)


def sign_konnect_order_webhook(order_id: int) -> str:
    """
    Même principe que `sign_konnect_webhook`, pour le webhook de paiement
    carte d'une COMMANDE (modèle direct, connexion Konnect au paiement carte,
    2026-08-19) — domaine séparé (préfixe `order:`) : une signature de
    commande ne doit jamais pouvoir être rejouée comme signature de
    restaurant, ni réciproquement.
    """
    return hmac.new(_webhook_key(), f"order:{order_id}".encode("utf-8"), sha256).hexdigest()


def verify_konnect_order_webhook(order_id: int, sig: str) -> bool:
    if not sig:
        return False
    return hmac.compare_digest(sign_konnect_order_webhook(order_id), sig)


class KonnectError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class KonnectPayment:
    id: str
    status: str
    amount: int
    reached_amount: int
    order_id: str | None = None


def _headers(api_key: str | None = None) -> dict[str, str]:
    key = api_key or os.environ.get("KONNECT_API_KEY")
    if not key:
        raise KonnectError("KONNECT_API_KEY manquante")
    return {"Content-Type": "application/json", "x-api-key": key}


def init_konnect_payment(
    *,
    amount_tnd: float,
    order_id: str,
    description: str,
    webhook: str,
    success_url: str,
    fail_url: str,
    lifespan_minutes: int,
    api_key: str | None = None,
    receiver_wallet_id: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
) -> tuple[str, str]:
    """
    Initialise un paiement. Le montant est TOUJOURS réglé en TND.

    `api_key`/`receiver_wallet_id` : identifiants explicites (wallet d'un
    restaurant précis, paiement carte du client — modèle direct, 2026-08-19).
    Absents, on retombe sur `KONNECT_API_KEY`/`KONNECT_RECEIVER_WALLET_ID`
    (wallet de Tawla elle-même, utilisé pour l'abonnement uniquement).

    Renvoie `(pay_url, payment_ref)` — rediriger vers `pay_url`, stocker
    `payment_ref` pour le règlement.
    """
    wallet_id = receiver_wallet_id or os.environ.get("KONNECT_RECEIVER_WALLET_ID")
    if not wallet_id:
        raise KonnectError("KONNECT_RECEIVER_WALLET_ID manquante")

    body: dict[str, Any] = {
        "receiverWalletId": wallet_id,
        "token": "TND",
        "amount": tnd_to_millimes(amount_tnd),
        "type": "immediate",
        "description": description,
        "acceptedPaymentMethods": _ACCEPTED_PAYMENT_METHODS,
        "lifespan": lifespan_minutes,
        "checkoutForm": False,
        "orderId": order_id,
        "webhook": webhook,
        "successUrl": success_url,
        "failUrl": fail_url,
        "theme": "light",
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phoneNumber": phone_number,
    }

    try:
        res = httpx.post(f"{KONNECT_API_URL}/payments/init-payment", headers=_headers(api_key), json=body, timeout=15)
    except httpx.HTTPError as err:
        raise KonnectError(f"init-payment réseau: {err}") from err

    if res.status_code >= 400:
        raise KonnectError(f"init-payment {res.status_code}: {res.text}", res.status_code)

    data = res.json()
    pay_url, payment_ref = data.get("payUrl"), data.get("paymentRef")
    if not pay_url or not payment_ref:
        raise KonnectError("Réponse init-payment incomplète")
    return pay_url, payment_ref


def get_konnect_payment(payment_ref: str, api_key: str | None = None) -> KonnectPayment:
    """Récupère les détails d'un paiement pour vérifier son statut — source de
    vérité côté serveur, jamais un statut transmis par le client."""
    try:
        res = httpx.get(f"{KONNECT_API_URL}/payments/{payment_ref}", headers=_headers(api_key), timeout=15)
    except httpx.HTTPError as err:
        raise KonnectError(f"get-payment réseau: {err}") from err

    if res.status_code >= 400:
        raise KonnectError(f"get-payment {res.status_code}: {res.text}", res.status_code)

    payment = res.json().get("payment")
    if not payment:
        raise KonnectError("Réponse get-payment incomplète")
    return KonnectPayment(
        id=payment["id"],
        status=payment["status"],
        amount=payment["amount"],
        reached_amount=payment["reachedAmount"],
        order_id=payment.get("orderId"),
    )
