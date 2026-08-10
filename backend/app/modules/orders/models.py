import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    """
    États explicites du flux décrit : client commande -> serveur confirme
    avec la table -> validation -> cuisine. Chaque transition est tracée
    (utile pour litiges + analytics), pas juste un booléen "validé".
    """
    PENDING_CONFIRMATION = "pending_confirmation"  # envoyée par le client, en attente du serveur
    CONFIRMED = "confirmed"                        # serveur a confirmé avec la table
    SENT_TO_KITCHEN = "sent_to_kitchen"             # visible sur l'écran cuisine
    IN_PREPARATION = "in_preparation"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING_CONFIRMATION)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_to_kitchen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Prise en charge (« claim ») par un serveur depuis le pool partagé —
    # base des stats "commandes par serveur/jour" (dashboard manager).
    taken_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    taken_by: Mapped["Staff | None"] = relationship()

    @property
    def taken_by_staff_name(self) -> str | None:
        return self.taken_by.name if self.taken_by else None


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    # On fige le nom/prix au moment de la commande : si le resto change le
    # prix du menu après coup, ça ne doit JAMAIS modifier une commande passée.
    menu_item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")
