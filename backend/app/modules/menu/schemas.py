from pydantic import BaseModel, ConfigDict


class MenuItemCreate(BaseModel):
    restaurant_id: int
    name: str
    description: str | None = None
    category: str = "Autre"
    price: float
    image_url: str | None = None


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


class MenuItemAvailability(BaseModel):
    is_available: bool


class MenuItemUpdate(BaseModel):
    """Mise à jour partielle depuis le dashboard resto — tous les champs sont optionnels."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = None
    image_url: str | None = None
