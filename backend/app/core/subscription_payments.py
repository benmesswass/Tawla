"""
Règlement du paiement en ligne d'un passage à un palier supérieur.

Deux modèles bien distincts, jamais mélangés :

- **Konnect (Tunisie) et l'ACTIVATION initiale Stripe (France)** : paiement
  ponctuel, réglé soit par un webhook (Konnect) soit par la page de retour
  (`?konnect=success` / `?stripe_subscription=success`, filet de sécurité
  Konnect en dev local) — même fonction `settle_subscription_payment` dans
  les deux cas, gardée par `subscription_payment_ref` (remis à null au
  règlement, jamais réglée deux fois pour la même référence).
- **Les RENOUVELLEMENTS Stripe (France, mode Netflix — retour utilisateur,
  2026-09-02)** : `settle_subscription_payment` ne les voit jamais passer.
  Un abonnement Stripe se facture tout seul chaque mois, sans qu'aucun
  `payment_ref` ne soit émis ni qu'aucune page de retour ne soit visitée —
  seul le webhook (`handle_stripe_subscription_event`) peut le confirmer.
  Konnect ne peut pas avoir cette forme : pas de carte enregistrée, pas de
  récurrence dans son API — ce deuxième modèle reste Stripe/France
  uniquement (MARCHE_FRANCE.md Phase F6 étape 4).

`Restaurant` est une ligne UNIQUE réutilisée à chaque paiement (souscription
initiale ET renouvellements), pas une nouvelle ligne par achat.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal

import stripe
from sqlalchemy.orm import Session

from app.core.analytics import capture_event
from app.core.dates import as_utc
from app.core.konnect import KonnectError, get_konnect_payment, tnd_to_millimes
from app.core.logging import get_logger, log_event
from app.core.markets import current_market
from app.core.stripe_gateway import StripeGatewayError, eur_to_cents, retrieve_checkout_session, retrieve_subscription
from app.core.subscription import SUBSCRIPTION_DURATION_DAYS, tier_price
from app.modules.tenants.models import Restaurant, SubscriptionTier

logger = get_logger("subscription_payments")

SettleResult = Literal["active", "pending", "not_found", "error"]
WebhookResult = Literal[
    "linked", "renewed", "cancellation_scheduled", "cancellation_reversed", "cancelled", "ignored", "not_found", "error"
]


def settle_subscription_payment(db: Session, restaurant_id: int) -> SettleResult:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        return "not_found"

    # Rien à régler : déjà réglé par un appel concurrent (webhook + retour
    # client arrivés en même temps), ou aucun paiement jamais initié.
    if not restaurant.subscription_payment_ref or not restaurant.subscription_pending_tier:
        return "pending"

    payment_ref = restaurant.subscription_payment_ref
    pending_tier = restaurant.subscription_pending_tier

    # Contrôle d'intégrité : montant réellement reçu jamais inférieur au prix
    # du palier — toujours recalculé côté serveur (jamais un montant transmis
    # par le client ou par le webhook lui-même). tier_price() : peut être
    # réduit par l'offre de lancement, voir
    # Restaurant.launch_promo_discount_percent — calculé ICI, avant la mise à
    # jour plus bas, tant que `restaurant.is_active` reflète encore l'état
    # PRÉ-paiement (la réduction ne s'applique qu'une fois, jamais à un
    # renouvellement).
    price = tier_price(restaurant, pending_tier)

    # Fournisseur résolu par current_market (un déploiement ne sert qu'un
    # marché) — jamais par la forme de payment_ref, qui ne le distingue pas.
    provider_label = "stripe" if current_market.payment_provider == "stripe" else "konnect"
    if current_market.payment_provider == "stripe":
        try:
            payment = retrieve_checkout_session(payment_ref)
        except StripeGatewayError as err:
            log_event(logger, "stripe.subscription_settle_fetch_failed", restaurant_id=restaurant_id, error=str(err))
            return "error"
        if payment.status != "completed":
            return "pending"
        expected_smallest_unit = eur_to_cents(price)
        reached_amount = payment.amount_total
        if reached_amount < expected_smallest_unit:
            log_event(
                logger, "stripe.subscription_amount_mismatch",
                restaurant_id=restaurant_id, expected=expected_smallest_unit, reached_amount=reached_amount,
            )
            return "error"
    else:
        try:
            payment = get_konnect_payment(payment_ref)
        except KonnectError as err:
            log_event(logger, "konnect.subscription_settle_fetch_failed", restaurant_id=restaurant_id, error=str(err))
            return "error"
        if payment.status != "completed":
            return "pending"
        expected_smallest_unit = tnd_to_millimes(price)
        reached_amount = payment.reached_amount
        if reached_amount < expected_smallest_unit:
            log_event(
                logger, "konnect.subscription_amount_mismatch",
                restaurant_id=restaurant_id, expected=expected_smallest_unit, reached_amount=reached_amount,
            )
            return "error"

    # Essentiel EST un abonnement de 30 jours comme Pro/Business (2026-08-20,
    # voir CLAUDE.md) — même calcul de période pour les trois. `is_active`
    # passe à `True` une bonne fois pour toutes (voir Restaurant.is_active/
    # is_usable) ; c'est `subscription_period_end` qui porte le renouvellement.
    now = datetime.now(timezone.utc)
    base = (
        as_utc(restaurant.subscription_period_end)
        if restaurant.subscription_period_end and as_utc(restaurant.subscription_period_end) > now
        else now
    )
    new_period_end = base + timedelta(days=SUBSCRIPTION_DURATION_DAYS)

    # Mise à jour gardée par `payment_ref` (pas par id seul) : c'est la garde
    # d'idempotence — voir docstring du module.
    updated = (
        db.query(Restaurant)
        .filter(Restaurant.id == restaurant.id, Restaurant.subscription_payment_ref == payment_ref)
        .update(
            {
                "subscription_tier": pending_tier,
                "subscription_period_end": new_period_end,
                "is_active": True,
                "has_paid_for_subscription": True,
                "subscription_payment_ref": None,
                "subscription_pending_tier": None,
            }
        )
    )
    db.commit()

    log_event(
        logger, f"{provider_label}.subscription_settled",
        restaurant_id=restaurant_id, tier=pending_tier.value, period_end=new_period_end.isoformat(),
        already_settled=updated == 0,
    )
    # Uniquement quand CET appel a effectué le règlement (pas un doublon
    # webhook/retour client concurrent sur la même référence — voir
    # docstring du module) : sinon purchase_completed serait émis deux fois
    # pour le même paiement.
    if updated:
        capture_event(
            str(restaurant_id), "purchase_completed",
            tier=pending_tier.value, amount_smallest_unit=expected_smallest_unit, currency=current_market.currency.code,
        )
    return "active"


def handle_stripe_subscription_event(db: Session, event: stripe.Event) -> WebhookResult:
    """
    Traite un webhook d'abonnement récurrent Stripe (voir docstring du
    module) — jamais appelée pour Konnect. Quatre évènements suffisent :

    - `checkout.session.completed` (mode="subscription") : premier paiement.
      Associe le restaurant au client/abonnement Stripe (`client_reference_id`
      porte le `restaurant_id`, posé à l'init — Stripe ne connaît rien de nos
      identifiants internes). N'applique PAS encore le palier ni la période :
      `invoice.paid` s'en charge juste après (même évènement Stripe pour le
      tout premier paiement ET chaque renouvellement, un seul chemin à
      maintenir plutôt que deux qui pourraient diverger).
    - `invoice.paid` : chaque échéance, y compris la première. Relit
      `current_period_end` depuis l'abonnement Stripe lui-même
      (`retrieve_subscription`) — jamais un `+30 jours` calculé nous-mêmes
      comme pour Konnect, Stripe gère ses propres cycles.
    - `customer.subscription.updated` : annulation DEMANDÉE depuis le
      portail (mode Netflix, retour utilisateur 2026-09-02) — la config par
      défaut du portail annule "à la fin de la période", jamais
      immédiatement, donc c'est CE webhook qui porte la nouvelle
      (`cancel_at_period_end`), pas `deleted` ci-dessous qui ne se
      déclenchera que bien plus tard. Gère aussi le sens inverse (reprise
      avant l'échéance).
    - `customer.subscription.deleted` : fin RÉELLE de l'abonnement, à
      l'échéance déjà payée (jamais avant — l'accès reste jusque-là, jamais
      coupé dans l'instant). Annuler, N'IMPORTE QUEL palier y compris
      Essentiel, veut dire PLUS AUCUN SERVICE (retour utilisateur,
      2026-09-02) — jamais un retour gratuit à Essentiel comme le ferait
      `effective_tier()` sur une simple expiration Konnect. `is_active`
      repasse à `False` : l'écran `ActivationRequired` (déjà existant) prend
      le relais.
    """
    event_type = event["type"]
    # `.to_dict()` : un `StripeObject` supporte `[...]` mais pas `.get()`
    # (AttributeError explicite du SDK) — converti une fois ici plutôt que de
    # jongler entre les deux accès plus bas.
    obj = event["data"]["object"].to_dict()

    if event_type == "checkout.session.completed":
        if obj.get("mode") != "subscription":
            return "ignored"
        restaurant_id = int(obj["client_reference_id"])
        restaurant = db.get(Restaurant, restaurant_id)
        if not restaurant:
            return "not_found"
        restaurant.stripe_customer_id = obj["customer"]
        restaurant.stripe_subscription_id = obj["subscription"]
        db.commit()
        log_event(logger, "stripe.subscription_linked", restaurant_id=restaurant_id)
        return "linked"

    if event_type == "invoice.paid":
        subscription_id = obj.get("subscription")
        if not subscription_id:
            return "ignored"
        restaurant = (
            db.query(Restaurant).filter(Restaurant.stripe_subscription_id == subscription_id).first()
        )
        if not restaurant:
            # Course rare avec checkout.session.completed pas encore traité —
            # Stripe retentera la livraison si on ne renvoie pas 200 ; on
            # préfère accepter sans effet plutôt que de bloquer la file.
            log_event(logger, "stripe.subscription_invoice_paid_unmatched", subscription_id=subscription_id)
            return "not_found"

        try:
            sub = retrieve_subscription(subscription_id)
        except StripeGatewayError as err:
            log_event(
                logger, "stripe.subscription_invoice_paid_fetch_failed",
                restaurant_id=restaurant.id, error=str(err),
            )
            return "error"

        restaurant.subscription_tier = SubscriptionTier(sub.tier)
        restaurant.subscription_period_end = sub.current_period_end
        restaurant.is_active = True
        restaurant.has_paid_for_subscription = True
        # Une rétrogradation éventuellement en attente vient de s'appliquer
        # (ou la phase suivante d'une programmation antérieure a démarré) —
        # plus rien "en attente" à partir de maintenant, voir
        # Restaurant.subscription_downgrade_pending_tier.
        restaurant.subscription_downgrade_pending_tier = None
        db.commit()
        log_event(
            logger, "stripe.subscription_renewed",
            restaurant_id=restaurant.id, tier=sub.tier, period_end=sub.current_period_end.isoformat(),
        )
        capture_event(str(restaurant.id), "purchase_completed", tier=sub.tier, currency=current_market.currency.code)
        return "renewed"

    if event_type == "customer.subscription.updated":
        # La config par défaut du portail Stripe annule "à la fin de la
        # période" (jamais immédiatement) : ce webhook, pas
        # `customer.subscription.deleted`, est le SEUL signal qu'une
        # annulation vient d'être demandée — `deleted` ne se déclenchera que
        # bien plus tard, à l'échéance déjà payée (retour utilisateur,
        # 2026-09-02 : "j'ai annulé côté Stripe mais aucun changement côté
        # Tawla" — ce webhook manquait). Gère aussi le sens inverse : un
        # manager peut reprendre son abonnement depuis le portail avant
        # l'échéance.
        subscription_id = obj["id"]
        restaurant = (
            db.query(Restaurant).filter(Restaurant.stripe_subscription_id == subscription_id).first()
        )
        if not restaurant:
            return "not_found"
        cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
        if restaurant.subscription_cancel_at_period_end == cancel_at_period_end:
            return "ignored"
        restaurant.subscription_cancel_at_period_end = cancel_at_period_end
        db.commit()
        log_event(
            logger, "stripe.subscription_cancel_at_period_end_changed",
            restaurant_id=restaurant.id, cancel_at_period_end=cancel_at_period_end,
        )
        return "cancellation_scheduled" if cancel_at_period_end else "cancellation_reversed"

    if event_type == "customer.subscription.deleted":
        subscription_id = obj["id"]
        restaurant = (
            db.query(Restaurant).filter(Restaurant.stripe_subscription_id == subscription_id).first()
        )
        if not restaurant:
            return "not_found"
        restaurant.stripe_subscription_id = None
        restaurant.subscription_cancel_at_period_end = False
        # Annuler, N'IMPORTE QUEL palier (y compris Essentiel), veut dire
        # "plus aucun service" — jamais un retour gratuit à Essentiel comme
        # le ferait `effective_tier()` sur une simple expiration Konnect
        # (retour utilisateur, 2026-09-02). L'écran `ActivationRequired`
        # (déjà existant) prend le relais et propose de repayer
        # `restaurant.subscription_tier` — volontairement inchangé ici, pour
        # réactiver au même palier plutôt que retomber sur Essentiel par
        # défaut.
        restaurant.is_active = False
        db.commit()
        log_event(logger, "stripe.subscription_cancelled", restaurant_id=restaurant.id)
        return "cancelled"

    return "ignored"
