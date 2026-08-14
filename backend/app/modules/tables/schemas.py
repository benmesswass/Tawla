from pydantic import BaseModel, ConfigDict, Field

from app.modules.tables.models import TableShape


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


class TablePlacement(BaseModel):
    """Une table posée sur le plan. Les coordonnées sont en pourcentage de la
    surface, bornées ici : une table ne doit pas pouvoir finir hors du plan."""

    table_id: int
    pos_x: float = Field(ge=0, le=100)
    pos_y: float = Field(ge=0, le=100)
    shape: TableShape = TableShape.ROUND


class PlanUpdate(BaseModel):
    """
    Le plan entier en une requête. Déplacer six tables ne doit pas produire six
    appels : c'est une seule action du manager, donc une seule écriture — et
    rien ne peut être enregistré à moitié.
    """

    placements: list[TablePlacement]
