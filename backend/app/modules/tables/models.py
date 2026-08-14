import secrets

import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

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
