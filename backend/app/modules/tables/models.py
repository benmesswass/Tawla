import secrets

import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
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
