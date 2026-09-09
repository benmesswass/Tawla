import secrets

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TableShape(str, enum.Enum):
    """
    Forme dessinée sur le plan de salle. Trois suffisent à rendre une salle
    reconnaissable ; au-delà on dessine un logiciel d'architecture, pas un
    outil de service.
    """
    ROUND = "round"
    SQUARE = "square"
    RECT = "rect"


class LandmarkKind(str, enum.Enum):
    """
    Repère fixe du plan — pas une table : rien à commander, rien à servir,
    juste un point pour se repérer (« la 4 est près de l'entrée »). Deux
    valeurs seulement, celles qu'on demande pour s'orienter dans une salle ;
    au-delà, un vrai plan de salle d'architecte prendrait le relais.
    """
    BAR = "bar"
    ENTRANCE = "entrance"


def generate_table_token() -> str:
    """
    Token opaque et non-devinable pour le QR code de la table.
    Ne JAMAIS utiliser l'id incrémental ici : un client pourrait
    deviner/scanner la table d'à côté en changeant un chiffre dans l'URL.
    """
    return secrets.token_urlsafe(16)


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)  # ex: "Table 5"
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, default=generate_table_token)
    assigned_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)

    # Zone de salle (ex: "Intérieur", "Terrasse", "Plage") — texte libre
    # comme MenuItem.category, pas un enum figé : tous les établissements
    # n'ont pas les mêmes zones (un café sans terrasse n'a besoin d'aucune).
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Position sur le plan de salle, en pourcentage de la surface (0-100) —
    # jamais en pixels : le plan se regarde sur un téléphone de 360 px comme
    # sur l'écran du bureau, et une position en pixels ne survivrait pas au
    # changement d'écran. `None` = table pas encore posée sur le plan.
    pos_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    pos_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    shape: Mapped[TableShape] = mapped_column(Enum(TableShape), default=TableShape.ROUND)
    # Nombre de couverts. C'est le réglage principal du plan : un restaurateur
    # pense « une table de 4 », pas « un carré ». La forme reste un détail
    # secondaire, et le nombre de chaises dessinées en découle.
    seats: Mapped[int] = mapped_column(Integer, default=4)

    # Occupation de la table — état explicite, pas dérivé (2026-09-09).
    # Posé dès le scan du QR (`service.py::get_table_by_qr_token`), quelle
    # que soit la durée passée à composer la commande ensuite : aucun
    # mécanisme technique (déconnexion, délai) ne doit le remettre à zéro
    # pendant que les clients sont encore à table. Seul un geste humain du
    # serveur ou du manager (`release_table`) le remet à `None` — jamais
    # dérivé des commandes en cours, contrairement au reste du plan de
    # salle (voir `orders/service.py::ACTIVE_STATUSES`).
    occupied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlanLandmark(Base):
    __tablename__ = "plan_landmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    kind: Mapped[LandmarkKind] = mapped_column(Enum(LandmarkKind), nullable=False)

    # La géométrie ne vit pas sur cette ligne mais dans ses tronçons : un
    # comptoir qui suit deux murs n'est pas un rectangle. L'aplatir en un
    # seul (pos_x/pos_y/width/height ici, PR #174) obligeait le manager à
    # poser trois « bars » distincts pour dessiner un U — trois étiquettes,
    # trois suppressions, alors qu'il n'y a qu'un bar dans la salle.
    parts: Mapped[list["PlanLandmarkPart"]] = relationship(
        back_populates="landmark",
        cascade="all, delete-orphan",
        order_by="PlanLandmarkPart.ordre",
        lazy="selectin",
    )


class PlanLandmarkPart(Base):
    """
    Un tronçon du repère — un rectangle, et rien de plus. Le repère est
    l'**union** de ses tronçons : un seul dessine un comptoir droit, deux en
    équerre un L, trois un U. La forme naît donc du geste (glisser, étirer,
    prolonger), jamais d'un préréglage à choisir dans une liste — même parti
    pris qu'à la PR #174, poussé jusqu'aux formes que le rectangle seul ne
    savait pas dire.
    """

    __tablename__ = "plan_landmark_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    landmark_id: Mapped[int] = mapped_column(
        ForeignKey("plan_landmarks.id"), nullable=False, index=True
    )
    # L'ordre du parcours du comptoir, pas un détail d'affichage : prolonger
    # accroche le nouveau tronçon au bout du dernier posé.
    ordre: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Coin haut-gauche du rectangle (pas son centre, contrairement à une
    # table) — c'est ce qui rend le glisser du coin bas-droit trivial :
    # largeur = position du pointeur - pos_x. En pourcentage de la surface,
    # comme pos_x/pos_y d'une table : le plan se regarde sur un téléphone de
    # 360 px comme sur l'écran du bureau, jamais en pixels.
    pos_x: Mapped[float] = mapped_column(Float, nullable=False)
    pos_y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)

    landmark: Mapped["PlanLandmark"] = relationship(back_populates="parts")


class ForcedTableRelease(Base):
    """
    Trace d'une table libérée alors qu'une commande n'était ni annulée ni
    servie-et-payée (2026-09-09, demande de Wassim) — jamais posée pour une
    libération normale (table déjà réglée), uniquement pour celle-ci :
    c'est l'exception qui justifie la note, pas la libération elle-même.

    But : que le manager sache quelle table a été libérée en plein service,
    par qui, quand, à quelle étape était la commande, et pourquoi (note
    obligatoire écrite par le serveur/manager sur le moment — voir
    `service.py::release_table`). Jamais modifiable après coup : une trace
    qu'on peut corriger n'en est plus une.
    """

    __tablename__ = "forced_table_releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
    released_by_staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Code technique de l'étape au moment de la libération (ex:
    # "sent_to_kitchen", "served_unpaid") — jamais recalculé après coup à
    # partir de la commande, qui peut avoir avancé depuis.
    order_status_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    # Obligatoire au niveau base aussi, pas seulement côté API : cette ligne
    # n'existe QUE parce qu'une note a été fournie (voir service.py).
    note: Mapped[str] = mapped_column(String(500), nullable=False)

    table: Mapped["Table"] = relationship()
    released_by: Mapped["Staff"] = relationship()  # noqa: F821 — résolu par le registre SQLAlchemy

    @property
    def table_label(self) -> str:
        return self.table.label

    @property
    def released_by_name(self) -> str:
        return self.released_by.name
