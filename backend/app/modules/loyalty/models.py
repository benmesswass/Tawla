from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Nombre de commandes payées avant qu'un article gratuit ne soit débloqué —
# constante volontairement non configurable pour l'instant (YAGNI : aucun
# besoin exprimé de le régler par resto, cf. ROADMAP.md).
LOYALTY_REWARD_THRESHOLD = 10


class LoyaltyMember(Base):
    """
    Fidélité identifiée par numéro de téléphone — aucun compte client dans
    Tawla (le parcours reste public par design), donc pas de mot de passe ni
    de vérification SMS. Le staff peut voir/valider la récompense en salle,
    ce qui borne le risque d'abus (gain limité à un article offert).
    """
    __tablename__ = "loyalty_members"
    __table_args__ = (UniqueConstraint("restaurant_id", "phone_number", name="uq_loyalty_restaurant_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    reward_available: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
