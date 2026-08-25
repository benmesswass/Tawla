"""
Client Stripe Connect — paiement carte du client en France (miroir de
core/konnect.py pour le marché `fr`, MARCHE_FRANCE.md C2/S1-S2).

Intégration OPTIONNELLE et à dégradation gracieuse, même principe que
Konnect : sans `Restaurant.stripe_account_id`, le paiement reste en mode
démonstration. Dès que ce compte est connecté ET que `PAYMENT_MODE=stripe`
est posé explicitement, le flux réel Stripe prend le relais — la simple
présence du compte ne suffit jamais à elle seule (anti-activation
accidentelle, même garde-fou que Konnect).

Modèle DIRECT CHARGE sur le compte connecté (`Stripe-Account: acct_…`) : le
restaurant est le marchand, les fonds se déposent directement sur son propre
compte Stripe — Tawla ne les touche jamais (MARCHE_FRANCE.md §3.1, ligne
324 : « le restaurant est le marchand »). Contrairement à Konnect, Stripe
signe lui-même ses webhooks (`Stripe-Signature`) : pas besoin de signer notre
propre URL comme pour Konnect.

**Statut au 2026-08-25 : câblé et testé (mocks), jamais activé en
production.** Aucun compte Stripe n'existe encore pour Tawla (ouverture du
compte = tâche humaine, MARCHE_FRANCE.md roadmap F6). Le bouton client reste
grisé pour le marché France indépendamment de cet interrupteur (voir
`frontend/lib/market.ts::onlinePaymentAvailable`) — décider d'activer
réellement le paiement en ligne en France dépend de l'arbitrage S1/S2 avec
l'expert-comptable (MARCHE_FRANCE.md §3.1), jamais deviné depuis une session
de code.

Doc : https://docs.stripe.com/api/checkout/sessions
      https://docs.stripe.com/connect/direct-charges
      https://docs.stripe.com/webhooks#verify-manually
"""
import hmac
import os
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import httpx

STRIPE_API_URL = os.environ.get("STRIPE_API_URL", "https://api.stripe.com/v1")

# Tolérance sur l'horodatage du webhook (anti-rejeu) — même valeur que la
# bibliothèque officielle Stripe.
_WEBHOOK_TOLERANCE_SECONDS = 300


def eur_to_cents(eur: float) -> int:
    """L'EUR est libellé en centimes par Stripe (1 EUR = 100 cents), comme
    toute devise à 2 décimales chez Stripe."""
    return round(eur * 100)


def is_stripe_enabled() -> bool:
    """
    Vrai si le paiement réel Stripe est ACTIF. Piloté EXPLICITEMENT par
    `PAYMENT_MODE=stripe` — lu à chaque appel (jamais mis en cache), même
    principe que `konnect.is_konnect_enabled()`. Un seul `PAYMENT_MODE`
    partagé : jamais `konnect` ET `stripe` actifs en même temps, cohérent
    avec un déploiement qui ne sert qu'un seul marché (MARCHE_FRANCE.md §4).
    """
    return os.environ.get("PAYMENT_MODE") == "stripe"


class StripeError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class StripePayment:
    id: str
    status: str  # `payment_status` Stripe : "paid" | "unpaid" | "no_payment_required"
    amount: int  # centimes
    reached_amount: int  # `amount_total` réellement réglé, centimes
    order_id: str | None = None


def _headers(api_key: str | None = None) -> dict[str, str]:
    key = api_key or os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise StripeError("STRIPE_SECRET_KEY manquante")
    headers = {"Authorization": f"Bearer {key}"}
    return headers


def init_stripe_payment(
    *,
    amount_eur: float,
    order_id: str,
    description: str,
    success_url: str,
    fail_url: str,
    connected_account_id: str,
    customer_email: str | None = None,
) -> tuple[str, str]:
    """
    Crée une Checkout Session en DIRECT CHARGE sur le compte connecté du
    restaurant (`Stripe-Account`) — les fonds s'y déposent directement,
    jamais sur le compte plateforme de Tawla.

    Renvoie `(pay_url, payment_ref)` — rediriger vers `pay_url` (session
    Checkout hébergée par Stripe), stocker `payment_ref` (id de session)
    pour le règlement.
    """
    body: dict[str, Any] = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": fail_url,
        "client_reference_id": order_id,
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][product_data][name]": description,
        "line_items[0][price_data][unit_amount]": eur_to_cents(amount_eur),
        "line_items[0][quantity]": 1,
    }
    if customer_email:
        body["customer_email"] = customer_email

    headers = _headers()
    headers["Stripe-Account"] = connected_account_id

    try:
        res = httpx.post(f"{STRIPE_API_URL}/checkout/sessions", headers=headers, data=body, timeout=15)
    except httpx.HTTPError as err:
        raise StripeError(f"checkout/sessions réseau: {err}") from err

    if res.status_code >= 400:
        raise StripeError(f"checkout/sessions {res.status_code}: {res.text}", res.status_code)

    data = res.json()
    pay_url, payment_ref = data.get("url"), data.get("id")
    if not pay_url or not payment_ref:
        raise StripeError("Réponse checkout/sessions incomplète")
    return pay_url, payment_ref


def get_stripe_payment(payment_ref: str, connected_account_id: str) -> StripePayment:
    """Récupère les détails d'une Checkout Session pour vérifier son statut —
    source de vérité côté serveur, jamais un statut transmis par le client."""
    headers = _headers()
    headers["Stripe-Account"] = connected_account_id

    try:
        res = httpx.get(f"{STRIPE_API_URL}/checkout/sessions/{payment_ref}", headers=headers, timeout=15)
    except httpx.HTTPError as err:
        raise StripeError(f"checkout/sessions réseau: {err}") from err

    if res.status_code >= 400:
        raise StripeError(f"checkout/sessions {res.status_code}: {res.text}", res.status_code)

    session = res.json()
    amount_total = session.get("amount_total")
    if amount_total is None:
        raise StripeError("Réponse checkout/sessions incomplète")
    return StripePayment(
        id=session["id"],
        status=session.get("payment_status", "unpaid"),
        amount=amount_total,
        reached_amount=amount_total if session.get("payment_status") == "paid" else 0,
        order_id=session.get("client_reference_id"),
    )


def verify_stripe_order_webhook(payload: bytes, sig_header: str | None) -> bool:
    """
    Vérifie la signature d'un webhook Stripe (`Stripe-Signature`), format
    `t=<horodatage>,v1=<signature>[,v0=...]` — contrairement à Konnect qui ne
    signe rien, Stripe signe chaque webhook lui-même : pas d'URL à signer
    nous-mêmes, juste ce header à revérifier.

    Rejette toute signature absente, falsifiée, ou trop ancienne (anti-rejeu,
    même tolérance que la bibliothèque officielle Stripe : 5 minutes).
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret or not sig_header:
        return False

    parts = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
    timestamp, signature = parts.get("t"), parts.get("v1")
    if not timestamp or not signature:
        return False

    try:
        if abs(time.time() - int(timestamp)) > _WEBHOOK_TOLERANCE_SECONDS:
            return False
    except ValueError:
        return False

    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
