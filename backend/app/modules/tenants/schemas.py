from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class RamadanModeUpdate(BaseModel):
    enabled: bool
    iftar_time: datetime | None = None
