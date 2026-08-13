from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.tenants.models import SubscriptionTier


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
    iftar_time: datetime | None
    cafe_mode_enabled: bool


class RestaurantOut(RestaurantPublicOut):
    """Vue **staff** : fiche complète, servie aux seules routes sous JWT et
    seulement pour son propre établissement."""

    slug: str
    created_at: datetime
    kitchen_sound_enabled: bool
    subscription_tier: SubscriptionTier


class RamadanModeUpdate(BaseModel):
    enabled: bool
    iftar_time: datetime | None = None


class CafeModeUpdate(BaseModel):
    enabled: bool


class KitchenSoundUpdate(BaseModel):
    enabled: bool
