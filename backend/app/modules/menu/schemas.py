from pydantic import BaseModel, ConfigDict, Field, model_validator


class MenuItemOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_delta: float


class MenuItemOptionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    min_select: int
    max_select: int
    options: list[MenuItemOptionOut]


class MenuItemOptionIn(BaseModel):
    """Un choix envoyé par le manager — sans id : le groupe est remplacé en
    bloc (voir MenuItemOptionGroupsUpdate), jamais édité choix par choix."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=60)
    price_delta: float = 0


class MenuItemOptionGroupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=60)
    min_select: int = Field(default=0, ge=0)
    max_select: int = Field(default=1, ge=1)
    options: list[MenuItemOptionIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _min_not_above_max(self) -> "MenuItemOptionGroupIn":
        if self.min_select > self.max_select:
            raise ValueError("min_select ne peut pas dépasser max_select")
        return self


class MenuItemOptionGroupsUpdate(BaseModel):
    """Remplace d'un bloc tous les groupes d'options d'un article — même
    principe que MenuSuggestionsUpdate : rejouable sans effet de bord."""

    model_config = ConfigDict(extra="forbid")

    groups: list[MenuItemOptionGroupIn]


class MenuRegimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MenuRegimesUpdate(BaseModel):
    """
    Remplace en bloc le vocabulaire de régimes du restaurant (« Halal »,
    « Végétarien », ou tout nom choisi par le manager) — même principe de
    remplacement en bloc que les suggestions et les groupes d'options.
    L'ordre envoyé devient l'ordre d'affichage.
    """

    model_config = ConfigDict(extra="forbid")

    names: list[str] = Field(default_factory=list)


class MenuItemRegimesUpdate(BaseModel):
    """Remplace en bloc les régimes cochés pour UN article, parmi le
    vocabulaire déjà défini pour le restaurant (voir MenuRegimesUpdate)."""

    model_config = ConfigDict(extra="forbid")

    regime_ids: list[int] = Field(default_factory=list)


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
    option_groups: list[MenuItemOptionGroupOut] = Field(default_factory=list)
    regimes: list[MenuRegimeOut] = Field(default_factory=list)


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
