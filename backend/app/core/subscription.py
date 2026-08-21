from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dates import as_utc
from app.modules.staff.dependencies import require_active_restaurant
from app.modules.staff.models import Staff
from app.modules.tenants.models import LaunchCampaignConfig, Restaurant, SubscriptionTier

# Chaque palier inclut tout ce qu'offre le précédent — Business a accès à
# tout ce que Pro a, Pro à tout ce qu'Essentiel a.
_TIER_RANK = {
    SubscriptionTier.ESSENTIEL: 0,
    SubscriptionTier.PRO: 1,
    SubscriptionTier.BUSINESS: 2,
}

# Prix payé en ligne (voir konnect.py / subscription_payments.py). Montants
# alignés sur lib/offer.ts (frontend) — source de vérité CÔTÉ SERVEUR : ne
# jamais faire confiance à un montant transmis par le client.
#
# ESSENTIEL est un abonnement de 30 jours comme PRO/BUSINESS (2026-08-20, voir
# CLAUDE.md — "chaque client doit payer 50 DT pour l'Essentiel, jamais
# gratuit, sauf promo activée par l'admin") : même mécanique de
# `subscription_period_end` que les deux autres. La seule différence est
# `Restaurant.is_active`/`is_usable` (tenants/models.py) : Essentiel étant le
# palier PLANCHER, il n'y a plus de repli gratuit en dessous quand la période
# expire sans renouvellement — le compte redevient bloqué plutôt que de
# retomber sur un palier gratuit, contrairement à PRO/BUSINESS qui retombent
# sur Essentiel (`effective_tier()`).
TIER_PRICES_TND = {
    SubscriptionTier.ESSENTIEL: 50,
    SubscriptionTier.PRO: 100,
    SubscriptionTier.BUSINESS: 150,
}

# Durée d'une période payée en ligne (offre à trois paliers, paiement en
# ligne du 2026-08-18 : palier unique, pas de prélèvement récurrent — Konnect
# ne le permet pas nativement, et ça correspond au modèle "sans commission"
# déjà retenu). Un palier fixé à la main par setup_restaurant.py n'a pas cette
# limite — voir Restaurant.subscription_period_end.
SUBSCRIPTION_DURATION_DAYS = 30

# Offre de lancement (2026-08-21, décidée par Wassim, rendue configurable le
# même jour) : réduction sur le premier mois Essentiel, accordée
# automatiquement aux N premiers établissements inscrits en self-service —
# voir staff/router.py::register (octroi), GET /api/v1/auth/launch-promo
# (affiché sur /signup) et platform_admin/router.py (réglages, écran admin).
# Valeurs par défaut = le lancement d'origine (100 %, 20 places), reproduites
# telles quelles par la migration qui a créé la table.
LAUNCH_CAMPAIGN_DEFAULT_DISCOUNT_PERCENT = 100
LAUNCH_CAMPAIGN_DEFAULT_MAX_GRANTS = 20

# Id fixe de la ligne singleton — jamais qu'une seule campagne active à la
# fois (YAGNI, voir LaunchCampaignConfig).
_LAUNCH_CAMPAIGN_ID = 1


def get_launch_campaign(db: Session) -> LaunchCampaignConfig:
    """
    Toujours cette fonction pour lire la campagne en cours, jamais une requête
    directe : crée la ligne singleton avec les valeurs par défaut si elle
    n'existe pas encore (ne devrait arriver qu'en tout premier démarrage,
    la migration l'insère déjà — filet de sécurité, pas le chemin normal).
    """
    config = db.get(LaunchCampaignConfig, _LAUNCH_CAMPAIGN_ID)
    if config is None:
        config = LaunchCampaignConfig(
            id=_LAUNCH_CAMPAIGN_ID,
            discount_percent=LAUNCH_CAMPAIGN_DEFAULT_DISCOUNT_PERCENT,
            max_grants=LAUNCH_CAMPAIGN_DEFAULT_MAX_GRANTS,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def launch_promo_grants_used(db: Session) -> int:
    return db.query(Restaurant).filter(Restaurant.launch_promo_discount_percent.is_not(None)).count()


def essentiel_price_tnd(restaurant: Restaurant) -> int:
    """
    Le prix RÉEL à payer pour Essentiel, réduction de lancement comprise —
    toujours cette fonction pour calculer un montant, jamais
    `TIER_PRICES_TND[ESSENTIEL]` en lecture directe dès qu'un restaurant est
    en jeu (checkout, vérification de règlement).

    La réduction, si elle existe, a été FIGÉE à l'inscription
    (`Restaurant.launch_promo_discount_percent`) — jamais recalculée depuis la
    campagne en cours, qui a pu changer depuis. Elle ne s'applique qu'une
    fois : `is_active` passe à `True` dès la première activation (gratuite à
    100 %, ou réglée à un taux partiel), donc `not restaurant.is_active`
    protège naturellement contre un rachat "à prix cassé" lors d'un
    renouvellement — voir Restaurant.is_active/launch_promo_discount_percent.
    """
    base = TIER_PRICES_TND[SubscriptionTier.ESSENTIEL]
    if restaurant.launch_promo_discount_percent is not None and not restaurant.is_active:
        return round(base * (100 - restaurant.launch_promo_discount_percent) / 100)
    return base


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

    def _dependency(staff: Staff = Depends(require_active_restaurant), db: Session = Depends(get_db)) -> Staff:
        restaurant = db.get(Restaurant, staff.restaurant_id)
        if not restaurant or not tier_includes(effective_tier(restaurant), minimum):
            raise upgrade_required_error(minimum)
        return staff

    return _dependency
