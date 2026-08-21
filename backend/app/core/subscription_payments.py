"""
Règlement du paiement en ligne d'un passage à un palier supérieur. Logique
partagée entre le webhook Konnect et la page de retour (`?konnect=success`),
appelée par la même fonction dans les deux cas — voir tenants/router.py.

`Restaurant` est une ligne UNIQUE réutilisée à chaque paiement (souscription
initiale ET renouvellements), pas une nouvelle ligne par achat : l'idempotence
contre la course webhook/retour ne peut donc pas reposer sur un statut qui
resterait identique d'un cycle à l'autre — elle repose sur
`subscription_payment_ref`, remis à null dès le règlement. Un règlement
concurrent pour la MÊME référence ne peut donc jamais s'appliquer deux fois,
et un ancien `payment_ref` rejoué après coup ne correspond simplement plus à
rien (introuvable dans le WHERE de la mise à jour).
"""
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.core.dates import as_utc
from app.core.konnect import KonnectError, get_konnect_payment, tnd_to_millimes
from app.core.logging import get_logger, log_event
from app.core.subscription import SUBSCRIPTION_DURATION_DAYS, tier_price_tnd
from app.modules.tenants.models import Restaurant

logger = get_logger("subscription_payments")

SettleResult = Literal["active", "pending", "not_found", "error"]


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

    try:
        payment = get_konnect_payment(payment_ref)
    except KonnectError as err:
        log_event(logger, "konnect.subscription_settle_fetch_failed", restaurant_id=restaurant_id, error=str(err))
        return "error"

    if payment.status != "completed":
        return "pending"

    # Contrôle d'intégrité : montant réellement reçu jamais inférieur au prix
    # du palier — toujours recalculé côté serveur (jamais un montant transmis
    # par le client ou par le webhook lui-même). tier_price_tnd() : peut être
    # réduit par l'offre de lancement, voir
    # Restaurant.launch_promo_discount_percent — calculé ICI, avant la mise à
    # jour plus bas, tant que `restaurant.is_active` reflète encore l'état
    # PRÉ-paiement (la réduction ne s'applique qu'une fois, jamais à un
    # renouvellement).
    price = tier_price_tnd(restaurant, pending_tier)
    expected_millimes = tnd_to_millimes(price)
    if payment.reached_amount < expected_millimes:
        log_event(
            logger, "konnect.subscription_amount_mismatch",
            restaurant_id=restaurant_id, expected_millimes=expected_millimes, reached_amount=payment.reached_amount,
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
        logger, "konnect.subscription_settled",
        restaurant_id=restaurant_id, tier=pending_tier.value, period_end=new_period_end.isoformat(),
        already_settled=updated == 0,
    )
    return "active"
