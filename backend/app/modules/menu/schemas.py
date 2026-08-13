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


class MenuCsvImport(BaseModel):
    """Contenu brut du fichier, envoyé tel quel : le parsing et les messages
    d'erreur ligne par ligne vivent dans `menu/csv_import.py`, partagé avec le
    script d'installation d'un pilote."""

    content: str
    # « Ce fichier est ma carte complète » : les articles absents du fichier
    # sont rendus indisponibles. Sans cette option, l'import ne fait
    # qu'ajouter et mettre à jour — un patron qui envoie trois nouveaux plats
    # ne doit pas voir le reste de sa carte disparaître.
    replace_existing: bool = False


class MenuCsvImportResult(BaseModel):
    """
    Les articles déjà connus (même nom) sont mis à jour, pas dupliqués : le
    geste réel est « j'ai corrigé mon fichier, remets-le ».
    """

    created_count: int
    updated_count: int
    disabled_count: int
    errors: list[str]


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
