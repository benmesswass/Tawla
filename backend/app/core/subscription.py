from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dates import as_utc
from app.modules.staff.dependencies import get_current_staff
from app.modules.staff.models import Staff
from app.modules.tenants.models import Restaurant, SubscriptionTier

# Chaque palier inclut tout ce qu'offre le précédent — Business a accès à
# tout ce que Pro a, Pro à tout ce qu'Essentiel a.
_TIER_RANK = {
    SubscriptionTier.ESSENTIEL: 0,
    SubscriptionTier.PRO: 1,
    SubscriptionTier.BUSINESS: 2,
}

# Prix du passage à un palier supérieur, payé en ligne (voir konnect.py /
# subscription_payments.py). Aucune entrée pour Essentiel : c'est le palier
# gratuit par défaut d'un compte auto-inscrit (/auth/register), jamais une
# cible de paiement — payer pour un palier qu'on a déjà gratuitement n'a pas
# de sens. Montants alignés sur lib/offer.ts (frontend) — source de vérité
# CÔTÉ SERVEUR : ne jamais faire confiance à un montant transmis par le client.
TIER_PRICES_TND = {
    SubscriptionTier.PRO: 100,
    SubscriptionTier.BUSINESS: 150,
}

# Durée d'une période payée en ligne (offre à trois paliers, paiement en
# ligne du 2026-08-18 : palier unique, pas de prélèvement récurrent — Konnect
# ne le permet pas nativement, et ça correspond au modèle "sans commission"
# déjà retenu). Un palier fixé à la main par setup_restaurant.py n'a pas cette
# limite — voir Restaurant.subscription_period_end.
SUBSCRIPTION_DURATION_DAYS = 30


def tier_includes(tier: SubscriptionTier, minimum: SubscriptionTier) -> bool:
    return _TIER_RANK[tier] >= _TIER_RANK[minimum]


def effective_tier(restaurant: Restaurant) -> SubscriptionTier:
    """
    Le palier réellement actif — jamais `restaurant.subscription_tier` en
    lecture directe pour du gating, toujours cette fonction. Si un palier
    payé en ligne a dépassé sa période de 30 jours sans renouvellement, il
    retombe à Essentiel, calculé à chaque lecture, sans jamais muter la
    colonne en base. Un palier fixé à la main (`subscription_period_end` à
    null — pilote géré par setup_restaurant.py, relation commerciale directe
    avec Wassim) reste, lui, sans expiration.
    """
    if restaurant.subscription_period_end is None:
        return restaurant.subscription_tier
    if as_utc(restaurant.subscription_period_end) > datetime.now(timezone.utc):
        return restaurant.subscription_tier
    return SubscriptionTier.ESSENTIEL


def upgrade_required_error(minimum: SubscriptionTier) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "UPGRADE_REQUIRED",
            "message": f"this feature requires the {minimum.value} plan or above",
            "required_tier": minimum.value,
        },
    )


def require_tier(minimum: SubscriptionTier):
    """
    `Depends(require_tier(SubscriptionTier.PRO))` sur une route staff — 403
    `UPGRADE_REQUIRED` si le palier du restaurant ne couvre pas la fonctionnalité.

    Pour les routes publiques (parcours client, sans staff authentifié), le
    même contrôle se fait à la main avec `tier_includes()` une fois le
    restaurant déjà chargé — voir `orders/service.py` (paiement carte,
    fidélité) et `notifications` (push).
    """

    def _dependency(staff: Staff = Depends(get_current_staff), db: Session = Depends(get_db)) -> Staff:
        restaurant = db.get(Restaurant, staff.restaurant_id)
        if not restaurant or not tier_includes(effective_tier(restaurant), minimum):
            raise upgrade_required_error(minimum)
        return staff

    return _dependency
