from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.dates import UtcDatetime
from app.core.subscription import effective_tier
from app.modules.tenants.models import Restaurant, SubscriptionTier


class RestaurantPublicOut(BaseModel):
    """
    Vue **client** d'un établissement, servie contre le `qr_token` d'une de ses
    tables. Strictement ce dont la page de commande se sert : le nom affiché en
    tête, et les réglages qui changent ce qu'elle propose (bannière et
    pré-commande iftar, mode café).

    Tout le reste en est absent volontairement — `subscription_tier` et `slug`
    sont des données commerciales, et `kitchen_sound_enabled` un réglage
    interne. Ajouter un champ ici, c'est le publier.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ramadan_mode_enabled: bool
    iftar_time: UtcDatetime | None
    cafe_mode_enabled: bool


class RestaurantOut(RestaurantPublicOut):
    """Vue **staff** : fiche complète, servie aux seules routes sous JWT et
    seulement pour son propre établissement."""

    slug: str
    created_at: UtcDatetime
    kitchen_sound_enabled: bool
    subscription_tier: SubscriptionTier
    subscription_period_end: UtcDatetime | None
    # Activation du compte (2026-08-20) — jamais sur RestaurantPublicOut,
    # donnée commerciale comme subscription_tier. Le frontend s'en sert pour
    # afficher l'écran de paiement (50 DT) tant que ni l'un ni l'autre n'est
    # vrai — voir Restaurant.is_usable.
    is_active: bool
    promo_gratuit: bool
    # Offre de lancement (2026-08-21, réglages configurables — voir
    # platform_admin) — le frontend s'en sert pour afficher le prix réduit
    # (ActivationRequired) et le rappel de paiement tant que
    # has_paid_for_subscription est faux, avec le compte à rebours dérivé de
    # subscription_period_end ci-dessus.
    launch_promo_discount_percent: int | None
    has_paid_for_subscription: bool
    # Jamais la clé API elle-même (voir Restaurant.konnect_credentials) —
    # juste de quoi afficher "connecté" et le wallet, qui n'est pas un secret.
    konnect_configured: bool
    konnect_wallet_id: str | None


def serialize_restaurant(restaurant: Restaurant) -> RestaurantOut:
    """
    À utiliser PARTOUT où un `Restaurant` est renvoyé au staff, jamais
    `RestaurantOut.model_validate(restaurant)` directement : `subscription_tier`
    doit refléter le palier EFFECTIF (voir app/core/subscription.py), pas la
    valeur brute en base, qui peut être un palier payé en ligne et expiré
    depuis sans jamais avoir été corrigée en base (calcul à la lecture, pas de
    mutation, voir effective_tier).
    """
    return RestaurantOut.model_validate(restaurant).model_copy(
        update={"subscription_tier": effective_tier(restaurant)}
    )


class RamadanModeUpdate(BaseModel):
    enabled: bool
    iftar_time: datetime | None = None


class CafeModeUpdate(BaseModel):
    enabled: bool


class KitchenSoundUpdate(BaseModel):
    enabled: bool


class KonnectCredentialsIn(BaseModel):
    """
    Connexion du wallet Konnect PROPRE au restaurant (modèle direct,
    2026-08-19) — jamais celui de Tawla. `wallet_id` n'est pas un secret
    (Konnect l'affiche en clair dans son propre dashboard) ; `api_key` l'est,
    chiffrée avant stockage (voir Restaurant.konnect_api_key_encrypted).
    """

    api_key: str = Field(min_length=1)
    wallet_id: str = Field(min_length=1)


class SubscriptionCheckoutIn(BaseModel):
    """Le palier VISÉ — jamais un montant : le prix est toujours recalculé
    côté serveur depuis TIER_PRICES_TND (app/core/subscription.py)."""

    tier: SubscriptionTier


class SubscriptionCheckoutOut(BaseModel):
    """
    `mode="demo"` : palier déjà appliqué, `restaurant` à jour, `pay_url` absent
    — aucun paiement réel tant que Konnect n'est pas activé (PAYMENT_MODE).
    `mode="konnect"` : palier PAS encore appliqué (il ne le sera qu'au
    règlement du paiement) — rediriger le manager vers `pay_url`.
    """

    mode: Literal["demo", "konnect"]
    restaurant: RestaurantOut | None = None
    pay_url: str | None = None
