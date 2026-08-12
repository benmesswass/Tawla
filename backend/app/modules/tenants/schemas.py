from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.tenants.models import SubscriptionTier


class RestaurantCreate(BaseModel):
    name: str
    slug: str


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_at: datetime
    ramadan_mode_enabled: bool
    iftar_time: datetime | None
    cafe_mode_enabled: bool
    kitchen_sound_enabled: bool
    subscription_tier: SubscriptionTier


class RamadanModeUpdate(BaseModel):
    enabled: bool
    iftar_time: datetime | None = None


class CafeModeUpdate(BaseModel):
    enabled: bool


class KitchenSoundUpdate(BaseModel):
    enabled: bool
