from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WaiterCall(Base):
    """
    Appel serveur indépendant du passage de commande — un client qui a
    besoin d'attention (question, pain en plus, addition orale...) sans
    forcément vouloir/pouvoir passer par le flux commande. Persisté (pas
    juste un WebSocket éphémère) : un serveur reconnecté après coupure doit
    quand même voir les appels encore en attente, même classe de bug que
    les demandes de paiement cash (audit du 2026-08-10).
    """
    __tablename__ = "waiter_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
