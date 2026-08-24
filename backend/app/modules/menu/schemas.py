from pydantic import BaseModel, ConfigDict, Field

from app.core.markets import current_market


def _default_is_halal() -> bool:
    """
    Vrai en Tunisie, faux en France (F5-A6, MARCHE_FRANCE.md) — jamais un
    défaut fixe : la quasi-totalité des restos tunisiens sont halal, ce n'est
    la norme nulle part ailleurs. `default_factory` plutôt que `default` : lu
    au moment de la requête, pas figé à l'import du module.
    """
    return current_market().code != "fr"


class MenuItemCreate(BaseModel):
    # `image_url` n'est pas un champ que le client écrit : il est calculé par la
    # route de dépôt de photo, qui seule vérifie le format et la taille. Le
    # laisser en chaîne libre rouvrirait un `javascript:` ou un `data:` à script
    # dans le `src` affiché aux clients. Champ inconnu = 422, pas une écriture
    # silencieuse.
    model_config = ConfigDict(extra="forbid")

    restaurant_id: int
    name: str
    description: str | None = None
    category: str = "Autre"
    price: float
    spice_level: int = Field(default=0, ge=0, le=3)
    allergens: str | None = None
    is_halal: bool = Field(default_factory=_default_is_halal)
    # F5-A6 : codes INCO séparés par une virgule, liste fermée côté client
    # (frontend/lib/allergens.ts) — voir MenuItem.allergen_codes.
    allergen_codes: str | None = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False


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
    allergen_codes: str | None
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool


class MenuItemAvailability(BaseModel):
    is_available: bool


class MenuSuggestionsUpdate(BaseModel):
    """Remplace d'un bloc les articles proposés avec un plat. Trois au maximum :
    au-delà, la proposition devient une deuxième carte et le client la referme."""

    suggested_item_ids: list[int] = Field(default_factory=list, max_length=3)


class MenuItemSuggestionsOut(BaseModel):
    menu_item_id: int
    suggested_items: list[MenuItemOut]


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
    """Mise à jour partielle depuis le dashboard resto — tous les champs sont optionnels.

    La photo ne s'édite pas ici : `PUT /{id}/image` et `DELETE /{id}/image` sont
    les seules portes d'entrée (voir MenuItemCreate)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = None
    spice_level: int | None = Field(default=None, ge=0, le=3)
    allergens: str | None = None
    is_halal: bool | None = None
    allergen_codes: str | None = None
    is_vegetarian: bool | None = None
    is_vegan: bool | None = None
    is_gluten_free: bool | None = None
