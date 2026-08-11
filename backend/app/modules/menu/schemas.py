from pydantic import BaseModel, ConfigDict, Field


class MenuItemCreate(BaseModel):
    restaurant_id: int
    name: str
    description: str | None = None
    category: str = "Autre"
    price: float
    image_url: str | None = None
    spice_level: int = Field(default=0, ge=0, le=3)
    allergens: str | None = None
    is_halal: bool = True


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    name: str
    description: str | None
    category: str
    price: float
    is_available: bool
    image_url: str | None
    spice_level: int
    allergens: str | None
    is_halal: bool


class MenuItemAvailability(BaseModel):
    is_available: bool


class MenuItemUpdate(BaseModel):
    """Mise à jour partielle depuis le dashboard resto — tous les champs sont optionnels."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = None
    image_url: str | None = None
    spice_level: int | None = Field(default=None, ge=0, le=3)
    allergens: str | None = None
    is_halal: bool | None = None
