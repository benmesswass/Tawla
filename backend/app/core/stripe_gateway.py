"""
Client Stripe Connect (passerelle de paiement française) — MARCHE_FRANCE.md
§4, Phase F6 étape 2 (StripeProvider derrière le port de F3).

Même principe de dégradation gracieuse que `core/konnect.py` : la présence
des clés ne suffit jamais seule à activer le paiement réel, il faut en plus
`PAYMENT_MODE=stripe` posé explicitement (anti-activation accidentelle) —
c'est le « drapeau de marché » de l'Annexe C2 (encaissement réel désactivé
par défaut en production, actif en démo : chaque déploiement pose
`PAYMENT_MODE` lui-même, aucune bascule automatique par marché).

Modèle DIRECT CHARGES : le compte connecté (`account_id`, futur
`Restaurant.stripe_account_id`) est le marchand, jamais Tawla — même
garantie que Konnect (`Restaurant.konnect_credentials()`) — sans commission
prélevée (sans objet tant que le paiement carte reste « sans commission sur
les commandes », MARCHE_FRANCE.md §3.4).

`account_id` optionnel sur `create_checkout_session`/`retrieve_checkout_session` :
absent, c'est une charge PLATEFORME directe (abonnement Tawla elle-même,
`subscription_payments.py`) — même clé secrète, mais sans `stripe_account`,
donc sans passer par un compte connecté. Présent, c'est un Direct Charge sur
CE compte restaurant. Jamais les deux usages mélangés dans un même appel.

Abonnement récurrent (`create_subscription_checkout_session`) : réservé à
l'abonnement TAWLA elle-même (jamais Connect, jamais `account_id`) — Konnect
ne sait pas facturer automatiquement chaque mois (pas de carte enregistrée,
pas de récurrence dans son API), donc ce modèle reste Stripe/France
uniquement (MARCHE_FRANCE.md Phase F6 étape 4). Une facturation qui se
déclenche toute seule chaque mois ne peut être confirmée que par un webhook
— jamais par une page de retour, qui suppose un client présent au moment du
règlement — d'où `construct_webhook_event` ci-dessous, contrairement au
webhook Connect encore volontairement absent (étape 5, paiement carte du
client, où le filet de sécurité `/pay/card/check` suffit).
"""
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import stripe

# Bornes imposées par Stripe Checkout pour `expires_at` : 30 minutes à 24 heures
# après la création de la session.
_MIN_LIFESPAN_MINUTES = 30
_MAX_LIFESPAN_MINUTES = 24 * 60


class StripeGatewayError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class StripeCheckoutStatus:
    status: str  # normalisé "completed" | "pending" — même vocabulaire que KonnectPayment.status
    amount_total: int  # centimes


def eur_to_cents(eur: float) -> int:
    """L'EUR est libellé en centimes par Stripe (1 EUR = 100 centimes)."""
    return round(eur * 100)


def is_stripe_enabled() -> bool:
    """
    Vrai si le paiement réel Stripe est ACTIF. Piloté EXPLICITEMENT par
    `PAYMENT_MODE=stripe` — lu à chaque appel (jamais mis en cache), même
    principe que `konnect.is_konnect_enabled()`.
    """
    return os.environ.get("PAYMENT_MODE") == "stripe"


def _secret_key() -> str:
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise StripeGatewayError("STRIPE_SECRET_KEY manquante")
    return key


def create_checkout_session(
    *,
    amount_eur: float,
    order_id: str,
    description: str,
    success_url: str,
    fail_url: str,
    lifespan_minutes: int,
    account_id: str | None = None,
) -> tuple[str, str]:
    """
    Initialise un paiement via Stripe Checkout — Direct Charge sur le compte
    connecté `account_id` s'il est fourni, sinon charge plateforme directe
    (voir docstring du module). Renvoie `(pay_url, payment_ref=session.id)` —
    rediriger vers `pay_url`, stocker `payment_ref` pour le règlement.
    """
    lifespan = max(_MIN_LIFESPAN_MINUTES, min(_MAX_LIFESPAN_MINUTES, lifespan_minutes))
    try:
        session = stripe.checkout.Session.create(
            api_key=_secret_key(),
            **({"stripe_account": account_id} if account_id else {}),
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": description},
                        "unit_amount": eur_to_cents(amount_eur),
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=fail_url,
            metadata={"order_id": order_id},
            expires_at=int(time.time()) + lifespan * 60,
        )
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err

    if not session.url or not session.id:
        raise StripeGatewayError("Réponse Checkout Session incomplète")
    return session.url, session.id


def create_connected_account(*, country: str) -> str:
    """
    Crée un compte Standard Connect pour un restaurant qui n'en a pas encore
    (`Restaurant.stripe_account_id` encore vide) — Standard, pas Express ni
    Custom : le restaurant porte lui-même sa relation contractuelle avec
    Stripe (facturation, obligations fiscales), Tawla n'est jamais
    intermédiaire. Renvoie l'`account_id`, à republier ensuite dans
    `create_onboarding_link`.
    """
    try:
        account = stripe.Account.create(type="standard", country=country, api_key=_secret_key())
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err
    return account.id


def create_onboarding_link(*, account_id: str, refresh_url: str, return_url: str) -> str:
    """
    Lien d'inscription hébergé par Stripe (Account Links) — le restaurant y
    saisit ses informations légales/bancaires directement chez Stripe,
    jamais transmises à ni stockées par Tawla. Choisi plutôt qu'OAuth : ne
    dépend d'aucun réglage préalable côté tableau de bord Connect (client_id,
    URI de redirection), seulement de la clé secrète déjà nécessaire partout
    ailleurs dans ce module.
    """
    try:
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
            api_key=_secret_key(),
        )
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err
    return link.url


def create_subscription_checkout_session(
    *,
    amount_eur: float,
    restaurant_id: int,
    tier: str,
    description: str,
    success_url: str,
    cancel_url: str,
    customer_email: str | None,
) -> tuple[str, str]:
    """
    Démarre un abonnement récurrent mensuel (mode Netflix, retour utilisateur
    2026-09-02) — jamais Connect, voir docstring du module. `client_reference_id`
    porte le `restaurant_id` : c'est ainsi que le webhook
    (`checkout.session.completed`) retrouve QUEL restaurant vient de payer,
    Stripe ne connaissant rien de nos identifiants internes. Renvoie
    `(pay_url, session_id)` — `session_id` n'est PAS le `subscription_id`
    final (créé par Stripe après paiement), seulement une référence
    temporaire pour la page de retour.
    """
    try:
        session = stripe.checkout.Session.create(
            api_key=_secret_key(),
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": description},
                        "unit_amount": eur_to_cents(amount_eur),
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            client_reference_id=str(restaurant_id),
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
            # `metadata` sur la session ET sur l'abonnement qu'elle crée : le
            # webhook `checkout.session.completed` lit le premier, un futur
            # `invoice.paid` (renouvellement) pourrait avoir besoin du second
            # sans avoir à rappeler la session d'origine.
            metadata={"restaurant_id": str(restaurant_id), "tier": tier},
            subscription_data={"metadata": {"restaurant_id": str(restaurant_id), "tier": tier}},
        )
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err

    if not session.url or not session.id:
        raise StripeGatewayError("Réponse Checkout Session incomplète")
    return session.url, session.id


@dataclass
class StripeSubscriptionStatus:
    tier: str  # metadata posée dans subscription_data à la création
    current_period_end: datetime


def retrieve_subscription(subscription_id: str) -> StripeSubscriptionStatus:
    """
    Relit un abonnement Stripe — source de vérité pour la prochaine échéance
    (`current_period_end`) à chaque `invoice.paid` (subscription_payments.py),
    jamais un `+30 jours` calculé nous-mêmes comme pour Konnect : Stripe gère
    ses propres cycles (mensuel, mais aussi les prorata/changements).
    """
    try:
        # `.to_dict()` : un `StripeObject` supporte `[...]` mais pas `.get()`
        # (AttributeError explicite du SDK).
        sub = stripe.Subscription.retrieve(subscription_id, api_key=_secret_key()).to_dict()
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err
    tier = sub.get("metadata", {}).get("tier")
    if not tier:
        raise StripeGatewayError(f"abonnement Stripe {subscription_id} sans metadata.tier")
    # `current_period_end` a migré de la racine de l'abonnement vers chaque
    # ligne d'abonnement (`items.data[]`) dans les versions API Stripe
    # récentes (constaté le 2026-09-02, stripe==15.6.0) — jamais l'ancien
    # champ racine, absent désormais (KeyError). Un seul item ici : jamais
    # plus d'une ligne par abonnement (un seul palier à la fois, voir
    # create_subscription_checkout_session).
    items = sub.get("items", {}).get("data", [])
    if not items:
        raise StripeGatewayError(f"abonnement Stripe {subscription_id} sans ligne d'abonnement")
    return StripeSubscriptionStatus(
        tier=tier, current_period_end=datetime.fromtimestamp(items[0]["current_period_end"], tz=timezone.utc)
    )


def release_schedule_if_any(*, subscription_id: str) -> None:
    """
    Annule une rétrogradation programmée (`schedule_tier_change`) avant un
    upgrade immédiat — sans ça, la phase 2 déjà en place continuerait à se
    déclencher à l'échéance et écraserait l'upgrade qu'on vient de faire
    (retour utilisateur, 2026-09-02 : Pro avec Essentiel programmé, puis
    upgrade vers Business — la programmation devait être annulée, pas
    ignorée). `SubscriptionSchedule.release` rend l'abonnement à son état
    normal (prix de la phase EN COURS conservé), sans toucher au prix —
    `change_tier_immediately`, appelé juste après par l'appelant, s'occupe
    du changement lui-même.
    """
    sub = stripe.Subscription.retrieve(subscription_id, api_key=_secret_key()).to_dict()
    schedule_id = sub.get("schedule")
    if not schedule_id:
        return
    try:
        stripe.SubscriptionSchedule.release(schedule_id, api_key=_secret_key())
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err


def change_tier_immediately(
    *, subscription_id: str, new_tier: str, new_amount_eur: float, description: str
) -> None:
    """
    Change de palier SUR L'ABONNEMENT EXISTANT, effet immédiat, prorata
    facturé tout de suite (`proration_behavior="always_invoice"`) — jamais
    une nouvelle session de paiement empilée à côté (bug réel corrigé le
    2026-09-02 : chaque clic sur "Passer à X" créait un SECOND abonnement
    Stripe sans annuler le précédent, donc une vraie double facturation
    chaque mois — retour utilisateur : "ça change automatique la somme
    prélevée ??"). `create_subscription_checkout_session` (nouvelle session)
    ne sert donc plus QUE pour le tout premier abonnement, quand
    `Restaurant.stripe_subscription_id` est encore vide — voir l'appelant
    dans tenants/router.py.

    `product_data` (pas `product=<id de l'ancien item>`) : constaté en
    conditions réelles le 2026-09-02, Stripe marque inactif le produit
    ad hoc créé par `price_data` dès qu'un des abonnements qui l'utilisait
    est annulé — le réutiliser fait échouer TOUT changement de palier
    ultérieur ("product ... is marked as inactive"). `price_data.product_data`
    (création de produit à la volée), qui aurait évité ça, n'est accepté
    QUE par `checkout.Session.create` — `Subscription.modify` rejette ce
    paramètre ("unknown parameter", constaté le 2026-09-02) et exige un
    `product` existant. D'où `stripe.Product.create` explicite juste avant :
    un produit frais à chaque changement, jamais de dépendance à un état
    Stripe invisible d'ici.

    `metadata={"tier": new_tier}` posé sur l'ABONNEMENT lui-même (pas
    seulement sur le nouvel item de prix) : c'est lui que relit
    `retrieve_subscription` à chaque `invoice.paid` — sans cette mise à
    jour, le webhook de confirmation réappliquerait l'ANCIEN palier.
    """
    try:
        sub = stripe.Subscription.retrieve(subscription_id, api_key=_secret_key()).to_dict()
        current_item = sub["items"]["data"][0]
        product = stripe.Product.create(name=description, api_key=_secret_key())
        stripe.Subscription.modify(
            subscription_id,
            api_key=_secret_key(),
            items=[
                {
                    "id": current_item["id"],
                    "price_data": {
                        "currency": "eur",
                        "product": product.id,
                        "unit_amount": eur_to_cents(new_amount_eur),
                        "recurring": {"interval": "month"},
                    },
                }
            ],
            proration_behavior="always_invoice",
            metadata={"tier": new_tier},
        )
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err


def schedule_tier_change(*, subscription_id: str, new_tier: str, new_amount_eur: float, description: str) -> None:
    """
    Programme un passage vers un palier INFÉRIEUR à la PROCHAINE échéance
    déjà payée — jamais immédiat, jamais de prorata (retour utilisateur,
    2026-09-02 : Pro/Business peuvent revenir à un palier moins cher en
    restant abonnés, distinct d'une annulation complète). Contrairement à un
    passage à un palier SUPÉRIEUR (`change_tier_immediately` ci-dessus, sur
    ce même abonnement), la baisse de prix attend le prochain cycle : pas de
    remboursement partiel à calculer.

    Mécanisme Stripe : convertit l'abonnement en Subscription Schedule à
    deux phases — la phase en cours, INCHANGÉE, qui se termine à l'échéance
    déjà en base ; puis une nouvelle phase, au nouveau prix, qui démarre à
    cette même date. `invoice.paid` (subscription_payments.py) confirmera
    le changement de palier à cette date, exactement comme un renouvellement
    normal — `metadata.tier` sur la nouvelle phase, relu par
    `retrieve_subscription` comme pour n'importe quel autre cycle.

    Un abonnement ne peut être attaché qu'à UNE SEULE Subscription Schedule
    à la fois — Stripe refuse d'en créer une seconde par `from_subscription`
    tant que la précédente existe ("cannot migrate a subscription that is
    already attached to a schedule", constaté le 2026-09-02 : un manager qui
    change deux fois d'avis, ou reclique après une première programmation,
    tombait sur une 502). Si une programmation existe déjà pour CET
    abonnement (`sub["schedule"]`), on la MODIFIE à la place d'en recréer
    une — un manager qui se ravise programme simplement autre chose pour la
    même échéance, jamais une erreur.
    """
    try:
        sub = stripe.Subscription.retrieve(subscription_id, api_key=_secret_key()).to_dict()
        current_item = sub["items"]["data"][0]
        period_end = current_item["current_period_end"]

        existing_schedule_id = sub.get("schedule")
        if existing_schedule_id:
            schedule = stripe.SubscriptionSchedule.retrieve(existing_schedule_id, api_key=_secret_key()).to_dict()
        else:
            schedule = stripe.SubscriptionSchedule.create(
                from_subscription=subscription_id, api_key=_secret_key()
            ).to_dict()
        current_phase = schedule["phases"][0]
        # `product_data` (création à la volée) n'est accepté que par
        # `checkout.Session.create` — ni `Subscription.modify` ni
        # `SubscriptionSchedule.modify` ne le supportent ("unknown
        # parameter", constaté le 2026-09-02 sur le premier). Un produit
        # explicite, jamais celui de l'item courant (marqué inactif dès
        # qu'un abonnement qui l'utilisait est annulé — voir
        # change_tier_immediately).
        product = stripe.Product.create(name=description, api_key=_secret_key())

        stripe.SubscriptionSchedule.modify(
            schedule["id"],
            api_key=_secret_key(),
            end_behavior="release",
            phases=[
                {
                    "items": [{"price": current_item["price"]["id"], "quantity": 1}],
                    "start_date": current_phase["start_date"],
                    "end_date": period_end,
                    "proration_behavior": "none",
                },
                {
                    "items": [
                        {
                            "price_data": {
                                "currency": "eur",
                                "product": product.id,
                                "unit_amount": eur_to_cents(new_amount_eur),
                                "recurring": {"interval": "month"},
                            },
                            "quantity": 1,
                        }
                    ],
                    "start_date": period_end,
                    "metadata": {"tier": new_tier},
                    "proration_behavior": "none",
                },
            ],
        )
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err


def create_billing_portal_session(*, customer_id: str, return_url: str) -> str:
    """
    Portail Stripe hébergé (« Billing Portal ») où le manager gère lui-même
    son abonnement — annuler, voir ses factures — exactement le
    « comme Netflix » demandé (retour utilisateur, 2026-09-02) : jamais un
    écran d'annulation à écrire et maintenir côté Tawla, Stripe l'héberge et
    le tient à jour (moyens de paiement, TVA, mentions légales).
    """
    try:
        portal = stripe.billing_portal.Session.create(api_key=_secret_key(), customer=customer_id, return_url=return_url)
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err
    return portal.url


def construct_webhook_event(*, payload: bytes, signature_header: str) -> stripe.Event:
    """
    Vérifie la signature Stripe (`Stripe-Signature`) et décode l'évènement —
    jamais `json.loads(payload)` directement, qui accepterait n'importe quel
    corps forgé. `STRIPE_WEBHOOK_SECRET` : distinct de `STRIPE_SECRET_KEY`,
    généré par Stripe au moment où l'endpoint est déclaré dans son tableau de
    bord (Développeurs > Webhooks) — absent tant que ça n'a pas été fait.
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise StripeGatewayError("STRIPE_WEBHOOK_SECRET manquante")
    try:
        return stripe.Webhook.construct_event(payload, signature_header, secret)
    except (stripe.error.SignatureVerificationError, ValueError) as err:
        raise StripeGatewayError(str(err)) from err


def retrieve_checkout_session(session_id: str, *, account_id: str | None = None) -> StripeCheckoutStatus:
    """Récupère le statut d'une session pour vérifier son règlement — source
    de vérité côté serveur, jamais un statut transmis par le client."""
    try:
        session = stripe.checkout.Session.retrieve(
            session_id, api_key=_secret_key(), **({"stripe_account": account_id} if account_id else {})
        )
    except stripe.StripeError as err:
        raise StripeGatewayError(str(err)) from err

    status = "completed" if session.payment_status == "paid" else "pending"
    return StripeCheckoutStatus(status=status, amount_total=session.amount_total or 0)
