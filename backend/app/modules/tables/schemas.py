from pydantic import BaseModel, ConfigDict, Field

from app.modules.tables.models import LandmarkKind, TableShape


class TableCreate(BaseModel):
    restaurant_id: int
    label: str
    zone: str | None = None


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    label: str
    qr_token: str
    assigned_staff_id: int | None
    zone: str | None
    pos_x: float | None
    pos_y: float | None
    shape: TableShape
    seats: int


class TableAssignStaff(BaseModel):
    staff_id: int


class TableUpdate(BaseModel):
    label: str
    zone: str | None = None


class TablePlanOut(BaseModel):
    """
    Vue **plan** d'une table, servie à tout membre de l'équipe : le serveur a
    besoin de lire la salle, pas de la gérer. Ne porte pas le `qr_token` —
    il n'a rien à faire dans un écran de service, et ce qui n'est pas envoyé
    ne peut pas fuiter.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    zone: str | None
    pos_x: float | None
    pos_y: float | None
    shape: TableShape
    seats: int


class TablePlacement(BaseModel):
    """Une table posée sur le plan. Les coordonnées sont en pourcentage de la
    surface, bornées ici : une table ne doit pas pouvoir finir hors du plan."""

    table_id: int
    pos_x: float = Field(ge=0, le=100)
    pos_y: float = Field(ge=0, le=100)
    shape: TableShape = TableShape.ROUND
    # Borné : deux couverts au minimum, huit au-delà desquels on dessine une
    # banquette de mariage, pas une table de restaurant.
    seats: int = Field(default=4, ge=1, le=12)


class PlanUpdate(BaseModel):
    """
    Le plan entier en une requête. Déplacer six tables ne doit pas produire six
    appels : c'est une seule action du manager, donc une seule écriture — et
    rien ne peut être enregistré à moitié.
    """

    placements: list[TablePlacement]


class LandmarkCreate(BaseModel):
    """
    Poser un repère : il naît déjà placé, pas de réserve pour un point qui
    n'a rien d'autre à régler qu'une position.

    `pos_x`/`pos_y` sont son coin haut-gauche (pas son centre, contrairement
    à une table) — `width`/`height` sont bornées large : un bar peut courir
    tout un mur, jamais avaler la salle entière ni disparaître en un point.
    """

    kind: LandmarkKind
    pos_x: float = Field(ge=0, le=100)
    pos_y: float = Field(ge=0, le=100)
    width: float = Field(default=12, ge=2, le=90)
    height: float = Field(default=7, ge=2, le=90)


class LandmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: LandmarkKind
    pos_x: float
    pos_y: float
    width: float
    height: float


class LandmarkMove(BaseModel):
    """Position ET dimensions : tout ce qu'un repère a de modifiable après sa
    création, comme TablePlacement pour une table (position + forme +
    couverts) — une seule écriture, jamais une route par attribut."""

    pos_x: float = Field(ge=0, le=100)
    pos_y: float = Field(ge=0, le=100)
    width: float = Field(ge=2, le=90)
    height: float = Field(ge=2, le=90)
