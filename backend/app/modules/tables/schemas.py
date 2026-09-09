from datetime import datetime

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
    occupied_at: datetime | None


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
    occupied_at: datetime | None


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


class LandmarkPart(BaseModel):
    """
    Un tronçon du repère — un rectangle. `pos_x`/`pos_y` sont son coin
    haut-gauche (pas son centre, contrairement à une table) ; `width`/`height`
    sont bornées large : un comptoir peut courir tout un mur, jamais avaler la
    salle entière ni disparaître en un point.
    """

    model_config = ConfigDict(from_attributes=True)

    pos_x: float = Field(ge=0, le=100)
    pos_y: float = Field(ge=0, le=100)
    width: float = Field(ge=2, le=90)
    height: float = Field(ge=2, le=90)


class LandmarkCreate(BaseModel):
    """
    Poser un repère : il naît déjà placé, pas de réserve pour un point qui
    n'a rien d'autre à régler qu'une position.

    Un seul rectangle à la pose — c'est le geste réel : on pose un comptoir
    droit, on le coude ensuite (PUT, `LandmarkShape`) si la salle le demande.
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
    parts: list[LandmarkPart]


class LandmarkShape(BaseModel):
    """
    Toute la forme du repère en une requête : la liste de ses tronçons,
    positions et dimensions comprises. Tout ce qu'un repère a de modifiable
    après sa création, comme `PlanUpdate` pour les tables — une seule
    écriture, jamais une route par attribut ni un tronçon à la fois.

    Bornée à quatre tronçons : un droit, un L, un U, un comptoir qui suit
    trois murs. Au-delà on dessine un logiciel d'architecture, pas un outil de
    service.
    """

    parts: list[LandmarkPart] = Field(min_length=1, max_length=4)
