import secrets

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
